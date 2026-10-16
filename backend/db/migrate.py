"""Apply the checked-in PostgreSQL migrations for the provisional schema."""

import os
from pathlib import Path

import psycopg


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured before running migrations")

    migration_dir = Path(__file__).resolve().parent / "migrations"
    migrations = sorted(migration_dir.glob("*_postgres.sql"))
    if not migrations:
        raise RuntimeError(f"No PostgreSQL migrations found in {migration_dir}")

    with psycopg.connect(database_url) as connection:
        for migration in migrations:
            for statement in migration.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    connection.execute(statement)
            print(f"Applied {migration.name}")


if __name__ == "__main__":
    main()
