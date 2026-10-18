"""
Persistent application store (PostgreSQL or SQLite).

Holds every piece of user-owned state: accounts, sessions, deals, proposals,
receipts, activity, chat history, per-user API keys and LLM usage. Every query
is scoped by ``user_id`` so one founder can never read another founder's data.

The backend is chosen from the connection string: ``postgresql://...`` uses
PostgreSQL via psycopg; anything else is treated as a SQLite file path.

Secrets (LLM API keys, SMTP passwords) are encrypted at rest with Fernet using
``APP_ENCRYPTION_KEY``, or a key generated once at ``APP_KEY_FILE``
(default: ``.app_encryption_key`` next to the SQLite file, or in ``data/`` for PostgreSQL).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

try:  # psycopg is only needed when DATABASE_URL points at PostgreSQL
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only without the dependency
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

PASSWORD_ITERATIONS = 310_000
SESSION_TTL = timedelta(days=7)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_salt {blob} NOT NULL,
    password_hash {blob} NOT NULL,
    role TEXT NOT NULL DEFAULT 'Founder & CEO',
    business_name TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    signature TEXT NOT NULL DEFAULT '',
    working_hours TEXT NOT NULL DEFAULT '09:30 - 18:30 (Mon-Fri)',
    max_discount_pct INTEGER NOT NULL DEFAULT 5,
    quiet_days_threshold INTEGER NOT NULL DEFAULT 3,
    active_llm_provider TEXT,
    kill_switch_active INTEGER NOT NULL DEFAULT 0,
    kill_switch_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    api_key_enc TEXT,
    model TEXT,
    base_url TEXT,
    updated_at TEXT NOT NULL,
    last_tested_at TEXT,
    last_test_ok INTEGER,
    last_test_message TEXT,
    PRIMARY KEY (user_id, provider)
);

CREATE TABLE IF NOT EXISTS email_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT NOT NULL,
    password_enc TEXT,
    from_email TEXT NOT NULL,
    use_ssl INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    last_tested_at TEXT,
    last_test_ok INTEGER,
    last_test_message TEXT
);

CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL DEFAULT '',
    stage TEXT NOT NULL,
    value_inr INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    do_not_contact INTEGER NOT NULL DEFAULT 0,
    last_contact_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposals (
    ref TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deal_id TEXT,
    kind TEXT NOT NULL DEFAULT 'email',
    deal_title TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    rendered_body TEXT NOT NULL,
    rendered_hash TEXT NOT NULL,
    policy_verdict TEXT NOT NULL,
    policy_reasons TEXT NOT NULL DEFAULT '[]',
    guards_checked TEXT NOT NULL DEFAULT '[]',
    facts_used TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    decided_at TEXT,
    receipt_id TEXT,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_ref TEXT NOT NULL,
    action_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    recipient_email TEXT,
    subject TEXT,
    rendered_hash TEXT NOT NULL,
    external_id TEXT,
    detail TEXT NOT NULL DEFAULT '',
    guards_checked TEXT NOT NULL DEFAULT '[]',
    timeline TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    action_ref TEXT,
    receipt_id TEXT,
    deal_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    seq INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_usage (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    purpose TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deals_user ON deals(user_id);
CREATE INDEX IF NOT EXISTS idx_proposals_user ON proposals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_usage_user ON llm_usage(user_id, created_at);

CREATE TABLE IF NOT EXISTS google_accounts (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    access_token_enc TEXT,
    refresh_token_enc TEXT NOT NULL,
    expires_at TEXT,
    scopes TEXT NOT NULL DEFAULT '',
    connected_at TEXT NOT NULL,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    account_id TEXT NOT NULL,
    token_enc TEXT,
    from_number TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    last_tested_at TEXT,
    last_test_ok INTEGER,
    last_test_message TEXT
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_verifier TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# Columns added after first release: (table, column, definition), applied on startup.
ADDED_COLUMNS = (
    ("chat_messages", "seq", "INTEGER NOT NULL DEFAULT 0"),
    ("proposals", "payload", "TEXT"),
    ("deals", "contact_phone", "TEXT NOT NULL DEFAULT ''"),
    ("users", "sandbox_enabled", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "sandbox_emails", "TEXT NOT NULL DEFAULT ''"),
    ("users", "sandbox_phones", "TEXT NOT NULL DEFAULT ''"),
    ("chat_messages", "meta", "TEXT"),
    ("receipts", "delivery_status", "TEXT"),
)

USER_PUBLIC_FIELDS = (
    "id",
    "email",
    "name",
    "role",
    "business_name",
    "timezone",
    "signature",
    "working_hours",
    "max_discount_pct",
    "quiet_days_threshold",
    "active_llm_provider",
    "kill_switch_active",
    "kill_switch_reason",
    "sandbox_enabled",
    "sandbox_emails",
    "sandbox_phones",
    "created_at",
)

PROFILE_EDITABLE_FIELDS = {
    "name",
    "role",
    "business_name",
    "timezone",
    "signature",
    "working_hours",
    "max_discount_pct",
    "quiet_days_threshold",
    "sandbox_enabled",
    "sandbox_emails",
    "sandbox_phones",
}

DEAL_EDITABLE_FIELDS = {
    "company",
    "title",
    "contact_name",
    "contact_email",
    "contact_phone",
    "stage",
    "value_inr",
    "notes",
    "do_not_contact",
    "last_contact_at",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) >= 8:
        return "••••" + value[-4:]
    return "••••"


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class EmailAlreadyRegisteredError(Exception):
    pass


def is_postgres_url(value: str) -> bool:
    return value.startswith(("postgres://", "postgresql://"))


def redact_dsn(dsn: str) -> str:
    """Hide the password in a connection string for logs and status pages."""
    return re.sub(r"//([^:/@]+):[^@]*@", r"//\1:***@", dsn)


class AppStore:
    """Thread-safe store over one connection (SQLite file or PostgreSQL), serialized with a lock."""

    def __init__(self, database: str | os.PathLike[str]):
        self.database = str(database)
        self.is_postgres = is_postgres_url(self.database)
        self._lock = threading.RLock()
        if self.is_postgres:
            if psycopg is None:
                raise RuntimeError("DATABASE_URL is PostgreSQL but psycopg is not installed")
            self.backend_label = f"PostgreSQL ({redact_dsn(self.database).split('@')[-1]})"
        else:
            if self.database != ":memory:":
                Path(self.database).parent.mkdir(parents=True, exist_ok=True)
            self.backend_label = f"SQLite ({Path(self.database).name})"
        self._conn: Any = self._connect()
        self._create_schema()
        self._fernet = Fernet(self._load_encryption_key())

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------
    def _connect(self) -> Any:
        if self.is_postgres:
            # prepare_threshold=None: no server-side prepared statements, which transaction
            # poolers (PgBouncer, Neon, Supabase) cannot share between clients.
            return psycopg.connect(
                self.database, autocommit=True, row_factory=dict_row, connect_timeout=10, prepare_threshold=None
            )
        conn = sqlite3.connect(self.database, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if self.database != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _create_schema(self) -> None:
        ddl = SCHEMA.replace("{blob}", "BYTEA" if self.is_postgres else "BLOB")
        with self._lock:
            if self.is_postgres:
                # Serialize concurrent first starts (several API workers) on one advisory lock.
                with self._conn.transaction():
                    self._conn.execute("SELECT pg_advisory_xact_lock(727274)")
                    for statement in filter(None, (part.strip() for part in ddl.split(";"))):
                        self._conn.execute(statement)
                    for table, column, definition in ADDED_COLUMNS:
                        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            else:
                self._conn.executescript(ddl)
                for table, column, definition in ADDED_COLUMNS:
                    columns = {row[1] for row in self._conn.execute(f"PRAGMA table_info({table})")}
                    if column not in columns:
                        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                self._conn.commit()

    def _load_encryption_key(self) -> bytes:
        env_key = os.getenv("APP_ENCRYPTION_KEY", "").strip()
        if env_key:
            return env_key.encode("ascii")
        if self.database == ":memory:":
            return Fernet.generate_key()
        key_file = os.getenv("APP_KEY_FILE", "").strip()
        if key_file:
            key_path = Path(key_file)
        elif self.is_postgres:
            key_path = Path(__file__).resolve().parents[2] / "data" / ".app_encryption_key"
        else:
            key_path = Path(self.database).with_name(".app_encryption_key")
        if key_path.exists():
            return key_path.read_bytes().strip()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key

    def _encrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return None

    def _sql(self, sql: str) -> str:
        # psycopg uses %-style placeholders, so literal % (e.g. in LIKE patterns) must be doubled.
        return sql.replace("%", "%%").replace("?", "%s") if self.is_postgres else sql

    def _run(self, sql: str, params: tuple[Any, ...], fetch: bool) -> Any:
        with self._lock:
            try:
                return self._execute(sql, params, fetch)
            except Exception as exc:
                # Reconnect once if PostgreSQL dropped the connection (server restart, idle timeout).
                if self.is_postgres and isinstance(exc, psycopg.OperationalError) and self._conn.closed:
                    self._conn = self._connect()
                    return self._execute(sql, params, fetch)
                raise

    def _execute(self, sql: str, params: tuple[Any, ...], fetch: bool) -> Any:
        cur = self._conn.execute(self._sql(sql), params)
        if fetch:
            return cur.fetchall()
        if not self.is_postgres:
            self._conn.commit()
        return cur.rowcount

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self._run(sql, params, fetch=True)]

    def _one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def _exec(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        return int(self._run(sql, params, fetch=False))

    def health_check(self) -> bool:
        try:
            self._one("SELECT 1 AS ok")
            return True
        except Exception:
            return False

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------
    # Users & sessions
    # ------------------------------------------------------------------
    @staticmethod
    def _is_unique_violation(exc: Exception) -> bool:
        if isinstance(exc, sqlite3.IntegrityError):
            return True
        return psycopg is not None and isinstance(exc, psycopg.errors.UniqueViolation)

    @staticmethod
    def _as_bytes(value: Any) -> bytes:
        return bytes(value) if isinstance(value, (memoryview, bytearray)) else value

    @staticmethod
    def _public_user(row: dict[str, Any]) -> dict[str, Any]:
        user = {k: row[k] for k in USER_PUBLIC_FIELDS}
        user["kill_switch_active"] = bool(user["kill_switch_active"])
        user["sandbox_enabled"] = bool(user["sandbox_enabled"])
        return user

    def create_user(
        self, *, name: str, email: str, password: str, business_name: str = ""
    ) -> dict[str, Any]:
        email = email.strip().lower()
        salt = secrets.token_bytes(16)
        user_id = f"usr_{uuid4().hex[:12]}"
        try:
            self._exec(
                """INSERT INTO users (id, email, name, password_salt, password_hash,
                   business_name, signature, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    email,
                    name.strip(),
                    salt,
                    _hash_password(password, salt),
                    business_name.strip(),
                    name.strip(),
                    iso(utcnow()),
                ),
            )
        except Exception as exc:
            if self._is_unique_violation(exc):
                raise EmailAlreadyRegisteredError(email) from exc
            raise
        user = self.get_user(user_id)
        assert user is not None
        return user

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
        if row is None:
            # Burn comparable time so response timing does not reveal registered emails.
            _hash_password(password, b"0" * 16)
            return None
        salt, stored = self._as_bytes(row["password_salt"]), self._as_bytes(row["password_hash"])
        if not hmac.compare_digest(_hash_password(password, salt), stored):
            return None
        return self._public_user(row)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._public_user(row) if row else None

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        fields = {k: v for k, v in updates.items() if k in PROFILE_EDITABLE_FIELDS}
        if "sandbox_enabled" in fields:
            fields["sandbox_enabled"] = 1 if fields["sandbox_enabled"] else 0
        if fields:
            assignments = ", ".join(f"{k} = ?" for k in fields)
            self._exec(
                f"UPDATE users SET {assignments} WHERE id = ?",
                (*fields.values(), user_id),
            )
        user = self.get_user(user_id)
        assert user is not None
        return user

    def set_kill_switch(self, user_id: str, active: bool, reason: str | None) -> dict[str, Any]:
        self._exec(
            "UPDATE users SET kill_switch_active = ?, kill_switch_reason = ? WHERE id = ?",
            (1 if active else 0, reason if active else None, user_id),
        )
        user = self.get_user(user_id)
        assert user is not None
        return user

    def set_active_provider(self, user_id: str, provider: str | None) -> None:
        self._exec("UPDATE users SET active_llm_provider = ? WHERE id = ?", (provider, user_id))

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = utcnow()
        self._exec(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_hash_token(token), user_id, iso(now), iso(now + SESSION_TTL)),
        )
        return token

    def user_for_session(self, token: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM sessions WHERE token_hash = ?", (_hash_token(token),))
        if row is None:
            return None
        if parse_iso(row["expires_at"]) <= utcnow():
            self.delete_session(token)
            return None
        return self.get_user(row["user_id"])

    def delete_session(self, token: str) -> None:
        self._exec("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))

    def delete_user(self, user_id: str) -> bool:
        """Delete an account; every user-owned row goes with it (ON DELETE CASCADE)."""
        return self._exec("DELETE FROM users WHERE id = ?", (user_id,)) > 0

    # ------------------------------------------------------------------
    # API keys (LLM providers)
    # ------------------------------------------------------------------
    def list_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._query("SELECT * FROM api_keys WHERE user_id = ? ORDER BY provider", (user_id,))
        result = []
        for row in rows:
            key = self._decrypt(row["api_key_enc"])
            result.append(
                {
                    "provider": row["provider"],
                    "has_key": bool(key),
                    "masked_key": mask_secret(key),
                    "model": row["model"],
                    "base_url": row["base_url"],
                    "updated_at": row["updated_at"],
                    "last_tested_at": row["last_tested_at"],
                    "last_test_ok": None if row["last_test_ok"] is None else bool(row["last_test_ok"]),
                    "last_test_message": row["last_test_message"],
                }
            )
        return result

    def get_api_key(self, user_id: str, provider: str) -> dict[str, Any] | None:
        row = self._one(
            "SELECT * FROM api_keys WHERE user_id = ? AND provider = ?", (user_id, provider)
        )
        if row is None:
            return None
        return {
            "provider": row["provider"],
            "api_key": self._decrypt(row["api_key_enc"]),
            "model": row["model"],
            "base_url": row["base_url"],
        }

    def upsert_api_key(
        self,
        user_id: str,
        provider: str,
        *,
        api_key: str | None,
        model: str | None,
        base_url: str | None,
    ) -> None:
        """Store provider config. ``api_key=None`` keeps the existing key."""
        existing = self._one(
            "SELECT api_key_enc FROM api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        enc = self._encrypt(api_key) if api_key else (existing or {}).get("api_key_enc")
        self._exec(
            """INSERT INTO api_keys (user_id, provider, api_key_enc, model, base_url, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, provider) DO UPDATE SET
                 api_key_enc = excluded.api_key_enc,
                 model = excluded.model,
                 base_url = excluded.base_url,
                 updated_at = excluded.updated_at,
                 last_tested_at = NULL, last_test_ok = NULL, last_test_message = NULL""",
            (user_id, provider, enc, model, base_url, iso(utcnow())),
        )

    def delete_api_key(self, user_id: str, provider: str) -> bool:
        return (
            self._exec(
                "DELETE FROM api_keys WHERE user_id = ? AND provider = ?", (user_id, provider)
            )
            > 0
        )

    def record_api_key_test(self, user_id: str, provider: str, ok: bool, message: str) -> None:
        self._exec(
            """UPDATE api_keys SET last_tested_at = ?, last_test_ok = ?, last_test_message = ?
               WHERE user_id = ? AND provider = ?""",
            (iso(utcnow()), 1 if ok else 0, message[:500], user_id, provider),
        )

    # ------------------------------------------------------------------
    # Email (SMTP) settings
    # ------------------------------------------------------------------
    def get_email_settings(self, user_id: str, *, include_secret: bool = False) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM email_settings WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        password = self._decrypt(row["password_enc"])
        data = {
            "host": row["host"],
            "port": row["port"],
            "username": row["username"],
            "from_email": row["from_email"],
            "use_ssl": bool(row["use_ssl"]),
            "has_password": bool(password),
            "masked_password": mask_secret(password),
            "updated_at": row["updated_at"],
            "last_tested_at": row["last_tested_at"],
            "last_test_ok": None if row["last_test_ok"] is None else bool(row["last_test_ok"]),
            "last_test_message": row["last_test_message"],
        }
        if include_secret:
            data["password"] = password
        return data

    def upsert_email_settings(
        self,
        user_id: str,
        *,
        host: str,
        port: int,
        username: str,
        password: str | None,
        from_email: str,
        use_ssl: bool,
    ) -> None:
        existing = self._one("SELECT password_enc FROM email_settings WHERE user_id = ?", (user_id,))
        enc = self._encrypt(password) if password else (existing or {}).get("password_enc")
        self._exec(
            """INSERT INTO email_settings
                 (user_id, host, port, username, password_enc, from_email, use_ssl, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 host = excluded.host, port = excluded.port, username = excluded.username,
                 password_enc = excluded.password_enc, from_email = excluded.from_email,
                 use_ssl = excluded.use_ssl, updated_at = excluded.updated_at,
                 last_tested_at = NULL, last_test_ok = NULL, last_test_message = NULL""",
            (user_id, host, port, username, enc, from_email, 1 if use_ssl else 0, iso(utcnow())),
        )

    def delete_email_settings(self, user_id: str) -> bool:
        return self._exec("DELETE FROM email_settings WHERE user_id = ?", (user_id,)) > 0

    def record_email_test(self, user_id: str, ok: bool, message: str) -> None:
        self._exec(
            """UPDATE email_settings SET last_tested_at = ?, last_test_ok = ?, last_test_message = ?
               WHERE user_id = ?""",
            (iso(utcnow()), 1 if ok else 0, message[:500], user_id),
        )

    # ------------------------------------------------------------------
    # Deals
    # ------------------------------------------------------------------
    @staticmethod
    def _deal_out(row: dict[str, Any]) -> dict[str, Any]:
        deal = dict(row)
        deal.pop("user_id", None)
        deal["do_not_contact"] = bool(deal["do_not_contact"])
        if deal.get("last_contact_at"):
            deal["days_quiet"] = max(0, (utcnow() - parse_iso(deal["last_contact_at"])).days)
        else:
            deal["days_quiet"] = None
        return deal

    def list_deals(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM deals WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
        )
        return [self._deal_out(r) for r in rows]

    def get_deal(self, user_id: str, deal_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM deals WHERE user_id = ? AND id = ?", (user_id, deal_id))
        return self._deal_out(row) if row else None

    def create_deal(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        deal_id = f"D-{uuid4().hex[:8].upper()}"
        now = iso(utcnow())
        self._exec(
            """INSERT INTO deals (id, user_id, company, title, contact_name, contact_email, contact_phone,
                 stage, value_inr, notes, do_not_contact, last_contact_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                deal_id,
                user_id,
                data["company"],
                data["title"],
                data["contact_name"],
                data.get("contact_email", ""),
                data.get("contact_phone", "") or "",
                data["stage"],
                int(data.get("value_inr", 0)),
                data.get("notes", ""),
                1 if data.get("do_not_contact") else 0,
                data.get("last_contact_at") or now,
                now,
                now,
            ),
        )
        deal = self.get_deal(user_id, deal_id)
        assert deal is not None
        return deal

    def update_deal(self, user_id: str, deal_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        fields = {k: v for k, v in updates.items() if k in DEAL_EDITABLE_FIELDS}
        if "do_not_contact" in fields:
            fields["do_not_contact"] = 1 if fields["do_not_contact"] else 0
        fields["updated_at"] = iso(utcnow())
        assignments = ", ".join(f"{k} = ?" for k in fields)
        changed = self._exec(
            f"UPDATE deals SET {assignments} WHERE user_id = ? AND id = ?",
            (*fields.values(), user_id, deal_id),
        )
        return self.get_deal(user_id, deal_id) if changed else None

    def delete_deal(self, user_id: str, deal_id: str) -> bool:
        return self._exec("DELETE FROM deals WHERE user_id = ? AND id = ?", (user_id, deal_id)) > 0

    # ------------------------------------------------------------------
    # Proposals
    # ------------------------------------------------------------------
    @staticmethod
    def _proposal_out(row: dict[str, Any]) -> dict[str, Any]:
        p = dict(row)
        p.pop("user_id", None)
        for key in ("policy_reasons", "guards_checked", "facts_used"):
            p[key] = json.loads(p[key] or "[]")
        p["payload"] = json.loads(p["payload"]) if p.get("payload") else None
        return p

    def create_proposal(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        ref = f"PA-{utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        now = utcnow()
        self._exec(
            """INSERT INTO proposals (ref, user_id, deal_id, kind, deal_title, contact_name,
                 contact_email, subject, rendered_body, rendered_hash, policy_verdict,
                 policy_reasons, guards_checked, facts_used, status, created_at, expires_at, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ref,
                user_id,
                data.get("deal_id"),
                data.get("kind", "email"),
                data["deal_title"],
                data["contact_name"],
                data["contact_email"],
                data["subject"],
                data["rendered_body"],
                data["rendered_hash"],
                data["policy_verdict"],
                json.dumps(data.get("policy_reasons", [])),
                json.dumps(data.get("guards_checked", [])),
                json.dumps(data.get("facts_used", [])),
                data.get("status", "pending"),
                iso(now),
                iso(now + timedelta(hours=48)),
                json.dumps(data["payload"]) if data.get("payload") is not None else None,
            ),
        )
        proposal = self.get_proposal(user_id, ref)
        assert proposal is not None
        return proposal

    def get_proposal(self, user_id: str, ref: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM proposals WHERE user_id = ? AND ref = ?", (user_id, ref))
        return self._proposal_out(row) if row else None

    def list_proposals(self, user_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self._query(
                "SELECT * FROM proposals WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (user_id, status),
            )
        else:
            rows = self._query(
                "SELECT * FROM proposals WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            )
        return [self._proposal_out(r) for r in rows]

    def update_proposal(self, user_id: str, ref: str, updates: dict[str, Any]) -> None:
        allowed = {
            "status",
            "decided_at",
            "receipt_id",
            "rendered_body",
            "rendered_hash",
            "subject",
            "policy_verdict",
            "policy_reasons",
        }
        fields = {k: v for k, v in updates.items() if k in allowed}
        if "policy_reasons" in fields:
            fields["policy_reasons"] = json.dumps(fields["policy_reasons"])
        if not fields:
            return
        assignments = ", ".join(f"{k} = ?" for k in fields)
        self._exec(
            f"UPDATE proposals SET {assignments} WHERE user_id = ? AND ref = ?",
            (*fields.values(), user_id, ref),
        )

    def has_pending_proposal_for_deal(self, user_id: str, deal_id: str) -> bool:
        return (
            self._one(
                "SELECT ref FROM proposals WHERE user_id = ? AND deal_id = ? AND status = 'pending'",
                (user_id, deal_id),
            )
            is not None
        )

    # ------------------------------------------------------------------
    # Receipts
    # ------------------------------------------------------------------
    @staticmethod
    def _receipt_out(row: dict[str, Any]) -> dict[str, Any]:
        r = dict(row)
        r.pop("user_id", None)
        r["guards_checked"] = json.loads(r["guards_checked"] or "[]")
        r["timeline"] = json.loads(r["timeline"] or "[]")
        return r

    def create_receipt(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        receipt_id = f"rcpt_{uuid4().hex[:12]}"
        self._exec(
            """INSERT INTO receipts (receipt_id, user_id, action_ref, action_kind, status,
                 recipient_email, subject, rendered_hash, external_id, detail, guards_checked,
                 timeline, created_at, delivery_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                receipt_id,
                user_id,
                data["action_ref"],
                data.get("action_kind", "email"),
                data["status"],
                data.get("recipient_email"),
                data.get("subject"),
                data["rendered_hash"],
                data.get("external_id"),
                data.get("detail", ""),
                json.dumps(data.get("guards_checked", [])),
                json.dumps(data.get("timeline", [])),
                iso(utcnow()),
                data.get("delivery_status"),
            ),
        )
        receipt = self.get_receipt(user_id, receipt_id)
        assert receipt is not None
        return receipt

    def get_receipt(self, user_id: str, ref_or_id: str) -> dict[str, Any] | None:
        row = self._one(
            """SELECT * FROM receipts WHERE user_id = ? AND (receipt_id = ? OR action_ref = ?)
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, ref_or_id, ref_or_id),
        )
        return self._receipt_out(row) if row else None

    def update_receipt_delivery(self, user_id: str, receipt_id: str, delivery_status: str, event: str) -> None:
        receipt = self.get_receipt(user_id, receipt_id)
        if receipt is None:
            return
        timeline = [*receipt["timeline"], {"timestamp": iso(utcnow()), "event": event}]
        self._exec(
            "UPDATE receipts SET delivery_status = ?, timeline = ? WHERE user_id = ? AND receipt_id = ?",
            (delivery_status, json.dumps(timeline), user_id, receipt_id),
        )

    def list_receipts(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM receipts WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )
        return [self._receipt_out(r) for r in rows]

    # ------------------------------------------------------------------
    # Activity
    # ------------------------------------------------------------------
    def add_activity(
        self,
        user_id: str,
        *,
        type: str,
        title: str,
        description: str = "",
        action_ref: str | None = None,
        receipt_id: str | None = None,
        deal_id: str | None = None,
    ) -> None:
        self._exec(
            """INSERT INTO activity (id, user_id, type, title, description, action_ref,
                 receipt_id, deal_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"evt_{uuid4().hex[:12]}",
                user_id,
                type,
                title,
                description,
                action_ref,
                receipt_id,
                deal_id,
                iso(utcnow()),
            ),
        )

    def list_activity(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM activity WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        for r in rows:
            r.pop("user_id", None)
        return rows

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def create_chat_session(self, user_id: str, title: str) -> dict[str, Any]:
        session_id = f"chat_{uuid4().hex[:12]}"
        now = iso(utcnow())
        self._exec(
            "INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, title[:80] or "New chat", now, now),
        )
        return {"id": session_id, "title": title[:80] or "New chat", "created_at": now, "updated_at": now}

    def get_chat_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        row = self._one(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? AND id = ?",
            (user_id, session_id),
        )
        return row

    def list_chat_sessions(self, user_id: str) -> list[dict[str, Any]]:
        return self._query(
            """SELECT s.id, s.title, s.created_at, s.updated_at,
                      (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count
               FROM chat_sessions s WHERE s.user_id = ? ORDER BY s.updated_at DESC""",
            (user_id,),
        )

    def rename_chat_session(self, user_id: str, session_id: str, title: str) -> None:
        self._exec(
            "UPDATE chat_sessions SET title = ? WHERE user_id = ? AND id = ?",
            (title[:80], user_id, session_id),
        )

    def delete_chat_session(self, user_id: str, session_id: str) -> bool:
        return (
            self._exec(
                "DELETE FROM chat_sessions WHERE user_id = ? AND id = ?", (user_id, session_id)
            )
            > 0
        )

    def add_chat_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        msg_id = f"msg_{uuid4().hex[:12]}"
        now = iso(utcnow())
        with self._lock:
            last = self._one(
                "SELECT COALESCE(MAX(seq), 0) AS seq FROM chat_messages WHERE session_id = ?", (session_id,)
            )
            self._exec(
                """INSERT INTO chat_messages
                     (id, session_id, user_id, role, content, provider, model, seq, created_at, meta)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg_id, session_id, user_id, role, content, provider, model,
                    int(last["seq"]) + 1, now, json.dumps(meta) if meta else None,
                ),
            )
        self._exec(
            "UPDATE chat_sessions SET updated_at = ? WHERE user_id = ? AND id = ?",
            (now, user_id, session_id),
        )
        return {
            "id": msg_id,
            "role": role,
            "content": content,
            "provider": provider,
            "model": model,
            "created_at": now,
            "meta": meta,
        }

    def list_chat_messages(self, user_id: str, session_id: str) -> list[dict[str, Any]]:
        rows = self._query(
            """SELECT id, role, content, provider, model, created_at, meta FROM chat_messages
               WHERE user_id = ? AND session_id = ? ORDER BY seq, created_at""",
            (user_id, session_id),
        )
        for row in rows:
            row["meta"] = json.loads(row["meta"]) if row.get("meta") else None
        return rows

    # ------------------------------------------------------------------
    # WhatsApp (Twilio or Meta Cloud API credentials per user)
    # ------------------------------------------------------------------
    def get_whatsapp_settings(self, user_id: str, *, include_secret: bool = False) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM whatsapp_settings WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        token = self._decrypt(row["token_enc"])
        data = {
            "provider": row["provider"],
            "account_id": row["account_id"],
            "from_number": row["from_number"],
            "has_token": bool(token),
            "masked_token": mask_secret(token),
            "updated_at": row["updated_at"],
            "last_tested_at": row["last_tested_at"],
            "last_test_ok": None if row["last_test_ok"] is None else bool(row["last_test_ok"]),
            "last_test_message": row["last_test_message"],
        }
        if include_secret:
            data["token"] = token
        return data

    def upsert_whatsapp_settings(
        self, user_id: str, *, provider: str, account_id: str, token: str | None, from_number: str
    ) -> None:
        existing = self._one("SELECT token_enc FROM whatsapp_settings WHERE user_id = ?", (user_id,))
        enc = self._encrypt(token) if token else (existing or {}).get("token_enc")
        self._exec(
            """INSERT INTO whatsapp_settings (user_id, provider, account_id, token_enc, from_number, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 provider = excluded.provider, account_id = excluded.account_id,
                 token_enc = excluded.token_enc, from_number = excluded.from_number,
                 updated_at = excluded.updated_at,
                 last_tested_at = NULL, last_test_ok = NULL, last_test_message = NULL""",
            (user_id, provider, account_id, enc, from_number, iso(utcnow())),
        )

    def delete_whatsapp_settings(self, user_id: str) -> bool:
        return self._exec("DELETE FROM whatsapp_settings WHERE user_id = ?", (user_id,)) > 0

    def record_whatsapp_test(self, user_id: str, ok: bool, message: str) -> None:
        self._exec(
            """UPDATE whatsapp_settings SET last_tested_at = ?, last_test_ok = ?, last_test_message = ?
               WHERE user_id = ?""",
            (iso(utcnow()), 1 if ok else 0, message[:500], user_id),
        )

    # ------------------------------------------------------------------
    # Google (OAuth tokens per user)
    # ------------------------------------------------------------------
    def create_oauth_state(self, user_id: str, state: str, code_verifier: str) -> None:
        self._exec("DELETE FROM oauth_states WHERE created_at < ?", (iso(utcnow() - timedelta(minutes=15)),))
        self._exec(
            "INSERT INTO oauth_states (state, user_id, code_verifier, created_at) VALUES (?, ?, ?, ?)",
            (state, user_id, self._encrypt(code_verifier), iso(utcnow())),
        )

    def consume_oauth_state(self, state: str) -> dict[str, Any] | None:
        """Return and delete a pending OAuth state if it exists and is under 10 minutes old."""
        with self._lock:
            row = self._one("SELECT * FROM oauth_states WHERE state = ?", (state,))
            if row is None:
                return None
            self._exec("DELETE FROM oauth_states WHERE state = ?", (state,))
        if parse_iso(row["created_at"]) < utcnow() - timedelta(minutes=10):
            return None
        return {"user_id": row["user_id"], "code_verifier": self._decrypt(row["code_verifier"])}

    def save_google_account(
        self,
        user_id: str,
        *,
        email: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str,
        scopes: str,
    ) -> None:
        existing = self._one("SELECT refresh_token_enc FROM google_accounts WHERE user_id = ?", (user_id,))
        refresh_enc = self._encrypt(refresh_token) if refresh_token else (existing or {}).get("refresh_token_enc")
        if not refresh_enc:
            raise ValueError("Google did not return a refresh token")
        self._exec(
            """INSERT INTO google_accounts
                 (user_id, email, access_token_enc, refresh_token_enc, expires_at, scopes, connected_at, last_error)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
               ON CONFLICT(user_id) DO UPDATE SET
                 email = excluded.email, access_token_enc = excluded.access_token_enc,
                 refresh_token_enc = excluded.refresh_token_enc, expires_at = excluded.expires_at,
                 scopes = excluded.scopes, connected_at = excluded.connected_at, last_error = NULL""",
            (user_id, email, self._encrypt(access_token), refresh_enc, expires_at, scopes, iso(utcnow())),
        )

    def get_google_account(self, user_id: str, *, include_tokens: bool = False) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM google_accounts WHERE user_id = ?", (user_id,))
        if row is None:
            return None
        account = {
            "email": row["email"],
            "scopes": [s for s in (row["scopes"] or "").split() if s],
            "connected_at": row["connected_at"],
            "expires_at": row["expires_at"],
            "last_error": row["last_error"],
        }
        if include_tokens:
            account["access_token"] = self._decrypt(row["access_token_enc"])
            account["refresh_token"] = self._decrypt(row["refresh_token_enc"])
        return account

    def update_google_access_token(self, user_id: str, access_token: str, expires_at: str) -> None:
        self._exec(
            "UPDATE google_accounts SET access_token_enc = ?, expires_at = ?, last_error = NULL WHERE user_id = ?",
            (self._encrypt(access_token), expires_at, user_id),
        )

    def set_google_error(self, user_id: str, message: str | None) -> None:
        self._exec("UPDATE google_accounts SET last_error = ? WHERE user_id = ?", (message, user_id))

    def delete_google_account(self, user_id: str) -> bool:
        return self._exec("DELETE FROM google_accounts WHERE user_id = ?", (user_id,)) > 0

    # ------------------------------------------------------------------
    # LLM usage
    # ------------------------------------------------------------------
    def record_usage(
        self,
        user_id: str,
        *,
        provider: str,
        model: str,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._exec(
            """INSERT INTO llm_usage (id, user_id, provider, model, purpose, input_tokens,
                 output_tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"use_{uuid4().hex[:12]}",
                user_id,
                provider,
                model,
                purpose,
                int(input_tokens or 0),
                int(output_tokens or 0),
                iso(utcnow()),
            ),
        )

    def usage_summary(self, user_id: str) -> list[dict[str, Any]]:
        return self._query(
            """SELECT provider, model, COUNT(*) AS requests,
                      SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens,
                      MAX(created_at) AS last_used_at
               FROM llm_usage WHERE user_id = ? GROUP BY provider, model
               ORDER BY last_used_at DESC""",
            (user_id,),
        )
