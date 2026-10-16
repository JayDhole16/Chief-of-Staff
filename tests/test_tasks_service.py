import pytest

from backend.services.tasks import (
    InvalidTaskTransitionError,
    SQLiteTaskRepository,
    TaskConflictError,
    TaskNotFoundError,
    TaskService,
)


@pytest.fixture
def task_service():
    repository = SQLiteTaskRepository()
    yield TaskService(repository)
    repository.close()


def _create(service: TaskService, message_id: str = "msg-1"):
    return service.create_task(
        workspace_id="workspace-a",
        contact_id="contact-1",
        deal_id="deal-1",
        deal_version=1,
        source_message_id=message_id,
        kind="human_reply",
        payload={"risk_flags": []},
    )


def test_create_is_scoped_and_idempotent(task_service: TaskService):
    task = _create(task_service)
    replay = _create(task_service)

    assert replay.task_id == task.task_id
    assert task_service.get_task(workspace_id="workspace-a", task_id=task.task_id) == task
    with pytest.raises(TaskNotFoundError):
        task_service.get_task(workspace_id="workspace-b", task_id=task.task_id)


def test_idempotency_key_cannot_be_reused_for_different_task_data(task_service: TaskService):
    _create(task_service)
    with pytest.raises(TaskConflictError, match="reused with different task data"):
        task_service.create_task(
            workspace_id="workspace-a",
            contact_id="other-contact",
            deal_id="deal-1",
            deal_version=1,
            source_message_id="msg-1",
            kind="human_reply",
        )


def test_task_transitions_use_optimistic_version_and_allow_only_valid_edges(
    task_service: TaskService,
):
    task = _create(task_service)
    active = task_service.transition(
        workspace_id="workspace-a",
        task_id=task.task_id,
        expected_version=1,
        status="in_progress",
    )
    assert active.version == 2
    with pytest.raises(TaskConflictError, match="not at version 1"):
        task_service.transition(
            workspace_id="workspace-a",
            task_id=task.task_id,
            expected_version=1,
            status="completed",
        )
    with pytest.raises(InvalidTaskTransitionError, match="Cannot transition"):
        task_service.transition(
            workspace_id="workspace-a",
            task_id=task.task_id,
            expected_version=2,
            status="in_progress",
        )


def test_task_requires_positive_deal_version(task_service: TaskService):
    with pytest.raises(ValueError, match="positive integer"):
        task_service.create_task(
            workspace_id="workspace-a",
            contact_id="contact-1",
            deal_id="deal-1",
            deal_version=0,
            source_message_id="msg-2",
            kind="human_reply",
        )
