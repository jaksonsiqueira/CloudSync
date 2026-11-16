"""Inicialização do SQLite e gerenciamento de conexões."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 1


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Banco versão {version} é mais novo que esta versão do aplicativo ({SCHEMA_VERSION})."
                )
            if version == 0:
                connection.executescript(
                    """
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        source_path TEXT NOT NULL,
                        destination_folder_id TEXT,
                        mode TEXT NOT NULL CHECK (mode IN ('backup', 'sync')),
                        schedule TEXT,
                        enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                        status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        files_total INTEGER NOT NULL DEFAULT 0,
                        files_processed INTEGER NOT NULL DEFAULT 0,
                        bytes_total INTEGER NOT NULL DEFAULT 0,
                        bytes_processed INTEGER NOT NULL DEFAULT 0,
                        error_summary TEXT
                    );
                    CREATE INDEX runs_task_started ON runs(task_id, started_at DESC);
                    PRAGMA user_version = 1;
                    """
                )

