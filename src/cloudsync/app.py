"""Composição inicial dos serviços de infraestrutura do CloudSync."""

from dataclasses import dataclass
from pathlib import Path

from cloudsync.config import get_app_paths
from cloudsync.logging_config import configure_logging
from cloudsync.storage.database import Database
from cloudsync.storage.repositories import RunRepository, TaskRepository


@dataclass(slots=True)
class AppServices:
    database: Database
    tasks: TaskRepository
    runs: RunRepository
    data_dir: Path


def initialize() -> AppServices:
    """Prepara armazenamento e logs e retorna os repositórios da aplicação."""
    paths = get_app_paths()
    configure_logging()
    database = Database(paths.database)
    database.initialize()
    return AppServices(
        database=database,
        tasks=TaskRepository(database),
        runs=RunRepository(database),
        data_dir=paths.data_dir,
    )

