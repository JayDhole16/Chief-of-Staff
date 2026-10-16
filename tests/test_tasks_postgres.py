import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from backend.services.tasks import (
    InvalidTaskTransitionError,
    PostgresTaskRepository,
    TaskConflictError,
    TaskNotFoundError,
    TaskService,
)

DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
def task_service():
    repository = PostgresTaskRepository(DATABASE_URL or "")
    workspace = f"test-{uuid4().hex}"
    try:
        yield TaskService(repository), workspace
    finally:
        try:
            if DATABASE_URL:
                with psycopg.connect(DATABASE_URL) as connection:
                    connection.execute(
                        "DELETE FROM tasks WHERE workspace_id = %s", (workspace,)
                    )
        finally:
            repository.close()


def test_postgres_task_round_trip_scope_and_idempotency(task_service):
    service, workspace = task_service
    task = service.create_task(
        workspace_id=workspace,
        contact_id="contact-1",
        deal_id="deal-1",
        deal_version=1,
        source_message_id="message-1",
        kind="reply",
        payload={"risk_flags": ["G08"]},
    )
    replay = service.create_task(
        workspace_id=workspace,
        contact_id="contact-1",
        deal_id="deal-1",
        deal_version=1,
        source_message_id="message-1",
        kind="reply",
        payload={"risk_flags": ["G08"]},
    )

    assert replay == task
    assert service.get_task(workspace_id=workspace, task_id=task.task_id) == task
    with pytest.raises(TaskNotFoundError):
        service.get_task(workspace_id=f"{workspace}-other", task_id=task.task_id)


def test_postgres_task_rejects_conflicting_replay(task_service):
    service, workspace = task_service
    service.create_task(
        workspace_id=workspace,
        contact_id="contact-1",
        deal_id="deal-1",
        deal_version=1,
        source_message_id="message-1",
        kind="reply",
        payload={},
    )

    with pytest.raises(TaskConflictError):
        service.create_task(
            workspace_id=workspace,
            contact_id="contact-1",
            deal_id="deal-2",
            deal_version=1,
            source_message_id="message-1",
            kind="reply",
            payload={},
        )


def test_postgres_task_concurrent_replay_is_idempotent(task_service):
    service, workspace = task_service

    def create_task():
        return service.create_task(
            workspace_id=workspace,
            contact_id="contact-1",
            deal_id="deal-1",
            deal_version=1,
            source_message_id="message-concurrent",
            kind="reply",
            payload={"source": "concurrent-test"},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        tasks = list(executor.map(lambda _: create_task(), range(16)))

    assert len({task.task_id for task in tasks}) == 1
    assert len({task.version for task in tasks}) == 1


def test_postgres_task_transition_uses_optimistic_version(task_service):
    service, workspace = task_service
    task = service.create_task(
        workspace_id=workspace,
        contact_id="contact-1",
        deal_id="deal-1",
        deal_version=1,
        source_message_id="message-1",
        kind="reply",
    )
    active = service.transition(
        workspace_id=workspace,
        task_id=task.task_id,
        expected_version=1,
        status="in_progress",
    )
    assert active.version == 2

    with pytest.raises(TaskConflictError):
        service.transition(
            workspace_id=workspace,
            task_id=task.task_id,
            expected_version=1,
            status="completed",
        )

    completed = service.transition(
        workspace_id=workspace,
        task_id=task.task_id,
        expected_version=2,
        status="completed",
    )
    assert completed.version == 3
    with pytest.raises(InvalidTaskTransitionError):
        service.transition(
            workspace_id=workspace,
            task_id=task.task_id,
            expected_version=3,
            status="open",
        )
