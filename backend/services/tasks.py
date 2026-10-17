"""Versioned task storage and state transitions for the provisional demo contract."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Literal, Protocol, cast
from uuid import uuid4

TaskStatus = Literal["open", "in_progress", "completed", "blocked", "cancelled"]

_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    "open": frozenset({"in_progress", "blocked", "cancelled"}),
    "in_progress": frozenset({"open", "completed", "blocked", "cancelled"}),
    "completed": frozenset(),
    "blocked": frozenset({"open", "cancelled"}),
    "cancelled": frozenset(),
}


class TaskNotFoundError(LookupError):
    """Raised when a task is absent or outside the requested workspace."""


class TaskConflictError(RuntimeError):
    """Raised when an idempotency key or expected task version conflicts."""


class TaskRepositoryUnavailableError(RuntimeError):
    """Raised when the task repository cannot serve readiness checks."""


class InvalidTaskTransitionError(ValueError):
    """Raised when a task state transition is not allowed."""


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    workspace_id: str
    contact_id: str
    deal_id: str
    deal_version: int
    source_message_id: str
    kind: str
    status: TaskStatus
    payload: dict[str, Any]
    version: int
    created_at: str
    updated_at: str


class TaskRepository(Protocol):
    def health_check(self) -> bool: ...

    def create(self, task: TaskRecord) -> TaskRecord: ...

    def get(self, workspace_id: str, task_id: str) -> TaskRecord: ...

    def transition(
        self,
        workspace_id: str,
        task_id: str,
        expected_version: int,
        status: TaskStatus,
        updated_at: str,
    ) -> TaskRecord: ...


class SQLiteTaskRepository:
    """SQLite-backed repository used by local development and deterministic tests."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(database), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        migration = Path(__file__).resolve().parents[1] / "db" / "migrations" / "0001_tasks.sql"
        self._connection.executescript(migration.read_text(encoding="utf-8"))

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def health_check(self) -> bool:
        with self._lock:
            try:
                self._connection.execute("SELECT 1")
            except sqlite3.Error as exc:
                raise TaskRepositoryUnavailableError("SQLite task repository is unavailable") from exc
        return True

    def create(self, task: TaskRecord) -> TaskRecord:
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT * FROM tasks WHERE workspace_id = ? AND source_message_id = ?",
                (task.workspace_id, task.source_message_id),
            ).fetchone()
            if existing is not None:
                saved = _record_from_row(existing)
                if (
                    saved.contact_id != task.contact_id
                    or saved.deal_id != task.deal_id
                    or saved.deal_version != task.deal_version
                    or saved.kind != task.kind
                    or saved.payload != task.payload
                ):
                    raise TaskConflictError(
                        "The source message idempotency key was reused with different task data"
                    )
                return saved
            self._connection.execute(
                """
                INSERT INTO tasks (
                    task_id, workspace_id, contact_id, deal_id, deal_version,
                    source_message_id, kind, status, payload_json, version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.workspace_id,
                    task.contact_id,
                    task.deal_id,
                    task.deal_version,
                    task.source_message_id,
                    task.kind,
                    task.status,
                    json.dumps(task.payload, sort_keys=True, separators=(",", ":")),
                    task.version,
                    task.created_at,
                    task.updated_at,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task.task_id,)
            ).fetchone()
            return _record_from_row(row)

    def get(self, workspace_id: str, task_id: str) -> TaskRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE workspace_id = ? AND task_id = ?",
                (workspace_id, task_id),
            ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id} not found in workspace {workspace_id}")
        return _record_from_row(row)

    def transition(
        self,
        workspace_id: str,
        task_id: str,
        expected_version: int,
        status: TaskStatus,
        updated_at: str,
    ) -> TaskRecord:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, version = version + 1, updated_at = ?
                WHERE workspace_id = ? AND task_id = ? AND version = ?
                """,
                (status, updated_at, workspace_id, task_id, expected_version),
            )
            if cursor.rowcount != 1:
                row = self._connection.execute(
                    "SELECT 1 FROM tasks WHERE workspace_id = ? AND task_id = ?",
                    (workspace_id, task_id),
                ).fetchone()
                if row is None:
                    raise TaskNotFoundError(
                        f"Task {task_id} not found in workspace {workspace_id}"
                    )
                raise TaskConflictError(f"Task {task_id} is not at version {expected_version}")
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE workspace_id = ? AND task_id = ?",
                (workspace_id, task_id),
            ).fetchone()
            return _record_from_row(row)


class PostgresTaskRepository:
    """PostgreSQL repository for the provisional task contract."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url must be configured")
        self._database_url = database_url

    def close(self) -> None:
        return None

    def health_check(self) -> bool:
        import psycopg

        try:
            with psycopg.connect(self._database_url) as connection:
                connection.execute("SELECT 1")
        except psycopg.Error as exc:
            raise TaskRepositoryUnavailableError("PostgreSQL task repository is unavailable") from exc
        return True

    def create(self, task: TaskRecord) -> TaskRecord:
        import psycopg
        from psycopg.rows import dict_row

        values = (
            task.task_id,
            task.workspace_id,
            task.contact_id,
            task.deal_id,
            task.deal_version,
            task.source_message_id,
            task.kind,
            task.status,
            json.dumps(task.payload, sort_keys=True, separators=(",", ":")),
            task.version,
            task.created_at,
            task.updated_at,
        )
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                INSERT INTO tasks (
                    task_id, workspace_id, contact_id, deal_id, deal_version,
                    source_message_id, kind, status, payload_json, version,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT (workspace_id, source_message_id) DO NOTHING
                RETURNING *
                """,
                values,
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT * FROM tasks
                    WHERE workspace_id = %s AND source_message_id = %s
                    """,
                    (task.workspace_id, task.source_message_id),
                ).fetchone()
                if row is None:
                    raise TaskConflictError("Task creation conflicted without an existing task")
                saved = _record_from_mapping(row)
                if (
                    saved.contact_id != task.contact_id
                    or saved.deal_id != task.deal_id
                    or saved.deal_version != task.deal_version
                    or saved.kind != task.kind
                    or saved.payload != task.payload
                ):
                    raise TaskConflictError(
                        "The source message idempotency key was reused with different task data"
                    )
                return saved
            return _record_from_mapping(row)

    def get(self, workspace_id: str, task_id: str) -> TaskRecord:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE workspace_id = %s AND task_id = %s",
                (workspace_id, task_id),
            ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id} not found in workspace {workspace_id}")
        return _record_from_mapping(row)

    def transition(
        self,
        workspace_id: str,
        task_id: str,
        expected_version: int,
        status: TaskStatus,
        updated_at: str,
    ) -> TaskRecord:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                UPDATE tasks
                SET status = %s, version = version + 1, updated_at = %s
                WHERE workspace_id = %s AND task_id = %s AND version = %s
                RETURNING *
                """,
                (status, updated_at, workspace_id, task_id, expected_version),
            ).fetchone()
            if row is not None:
                return _record_from_mapping(row)
            exists = connection.execute(
                "SELECT 1 FROM tasks WHERE workspace_id = %s AND task_id = %s",
                (workspace_id, task_id),
            ).fetchone()
        if exists is None:
            raise TaskNotFoundError(f"Task {task_id} not found in workspace {workspace_id}")
        raise TaskConflictError(f"Task {task_id} is not at version {expected_version}")


class TaskService:
    """Enforces scoped task creation, idempotency, and optimistic state changes."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(
        self,
        *,
        workspace_id: str,
        contact_id: str,
        deal_id: str,
        deal_version: int,
        source_message_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskRecord:
        required = {
            "workspace_id": workspace_id,
            "contact_id": contact_id,
            "deal_id": deal_id,
            "source_message_id": source_message_id,
            "kind": kind,
        }
        missing = [
            name
            for name, value in required.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if missing:
            raise ValueError(f"Task fields must be non-empty: {', '.join(missing)}")
        if not isinstance(deal_version, int) or isinstance(deal_version, bool) or deal_version < 1:
            raise ValueError("deal_version must be a positive integer")
        now = datetime.now(timezone.utc).isoformat()
        return self._repository.create(
            TaskRecord(
                task_id=f"task_{uuid4().hex}",
                workspace_id=workspace_id,
                contact_id=contact_id,
                deal_id=deal_id,
                deal_version=deal_version,
                source_message_id=source_message_id,
                kind=kind,
                status="open",
                payload=payload or {},
                version=1,
                created_at=now,
                updated_at=now,
            )
        )

    def get_task(self, *, workspace_id: str, task_id: str) -> TaskRecord:
        return self._repository.get(workspace_id, task_id)

    def transition(
        self,
        *,
        workspace_id: str,
        task_id: str,
        expected_version: int,
        status: TaskStatus,
    ) -> TaskRecord:
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")
        current = self._repository.get(workspace_id, task_id)
        if current.version != expected_version:
            raise TaskConflictError(f"Task {task_id} is not at version {expected_version}")
        if status not in _ALLOWED_TRANSITIONS.get(current.status, frozenset()):
            raise InvalidTaskTransitionError(
                f"Cannot transition task from {current.status} to {status}"
            )
        return self._repository.transition(
            workspace_id,
            task_id,
            expected_version,
            status,
            datetime.now(timezone.utc).isoformat(),
        )


def _record_from_row(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        task_id=row["task_id"],
        workspace_id=row["workspace_id"],
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        deal_version=row["deal_version"],
        source_message_id=row["source_message_id"],
        kind=row["kind"],
        status=cast(TaskStatus, row["status"]),
        payload=json.loads(row["payload_json"]),
        version=row["version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _record_from_mapping(row: dict[str, Any]) -> TaskRecord:
    payload = row["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return TaskRecord(
        task_id=row["task_id"],
        workspace_id=row["workspace_id"],
        contact_id=row["contact_id"],
        deal_id=row["deal_id"],
        deal_version=row["deal_version"],
        source_message_id=row["source_message_id"],
        kind=row["kind"],
        status=cast(TaskStatus, row["status"]),
        payload=payload,
        version=row["version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
