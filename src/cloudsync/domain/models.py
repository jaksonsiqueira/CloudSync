"""Modelos de domínio independentes de interface e persistência."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TaskMode(StrEnum):
    BACKUP = "backup"
    SYNC = "sync"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class BackupTask:
    id: int | None
    name: str
    source_path: str
    destination_folder_id: str | None
    mode: TaskMode = TaskMode.BACKUP
    schedule: str | None = None
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TaskRun:
    id: int | None
    task_id: int
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    files_total: int = 0
    files_processed: int = 0
    bytes_total: int = 0
    bytes_processed: int = 0
    error_summary: str | None = None

