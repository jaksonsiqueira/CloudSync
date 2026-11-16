"""Consultas e gravações de tarefas e execuções."""

import sqlite3
from datetime import datetime, timezone

from cloudsync.domain.models import BackupTask, RunStatus, TaskMode, TaskRun
from cloudsync.storage.database import Database


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _task_from_row(row: sqlite3.Row) -> BackupTask:
    return BackupTask(
        id=row["id"], name=row["name"], source_path=row["source_path"],
        destination_folder_id=row["destination_folder_id"], mode=TaskMode(row["mode"]),
        schedule=row["schedule"], enabled=bool(row["enabled"]),
        created_at=_parse_datetime(row["created_at"]), updated_at=_parse_datetime(row["updated_at"]),
    )


class TaskRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, task: BackupTask) -> BackupTask:
        now = _utc_now().isoformat()
        with self.database.connection() as connection:
            cursor = connection.execute(
                """INSERT INTO tasks (name, source_path, destination_folder_id, mode, schedule, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.name, task.source_path, task.destination_folder_id, task.mode.value,
                 task.schedule, int(task.enabled), now, now),
            )
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _task_from_row(row)

    def list_all(self, *, enabled_only: bool = False) -> list[BackupTask]:
        query = "SELECT * FROM tasks"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY name COLLATE NOCASE, id"
        with self.database.connection() as connection:
            rows = connection.execute(query).fetchall()
        return [_task_from_row(row) for row in rows]

    def get(self, task_id: int) -> BackupTask | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _task_from_row(row) if row else None

    def delete(self, task_id: int) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0


class RunRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, run: TaskRun) -> TaskRun:
        with self.database.connection() as connection:
            cursor = connection.execute(
                """INSERT INTO runs (task_id, status, started_at, finished_at, files_total,
                   files_processed, bytes_total, bytes_processed, error_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run.task_id, run.status.value, run.started_at.isoformat(),
                 run.finished_at.isoformat() if run.finished_at else None, run.files_total,
                 run.files_processed, run.bytes_total, run.bytes_processed, run.error_summary),
            )
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._from_row(row)

    def list_for_task(self, task_id: int, *, limit: int = 100) -> list[TaskRun]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM runs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
                (task_id, limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TaskRun:
        return TaskRun(
            id=row["id"], task_id=row["task_id"], status=RunStatus(row["status"]),
            started_at=_parse_datetime(row["started_at"]), finished_at=_parse_datetime(row["finished_at"]),
            files_total=row["files_total"], files_processed=row["files_processed"],
            bytes_total=row["bytes_total"], bytes_processed=row["bytes_processed"],
            error_summary=row["error_summary"],
        )

