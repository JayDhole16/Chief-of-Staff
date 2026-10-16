CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    deal_id TEXT NOT NULL,
    deal_version INTEGER NOT NULL CHECK (deal_version > 0),
    source_message_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'completed', 'blocked', 'cancelled')),
    payload_json JSONB NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (workspace_id, source_message_id)
);

CREATE INDEX IF NOT EXISTS ix_tasks_workspace_status_created
    ON tasks (workspace_id, status, created_at);

CREATE INDEX IF NOT EXISTS ix_tasks_workspace_deal
    ON tasks (workspace_id, deal_id, created_at);
