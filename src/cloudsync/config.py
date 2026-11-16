"""Caminhos e configuração local do aplicativo."""

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path
    database: Path
    log_dir: Path


def get_app_paths() -> AppPaths:
    """Retorna caminhos persistentes do CloudSync para o usuário atual."""
    data_dir = user_data_path("CloudSync", appauthor=False, ensure_exists=True)
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return AppPaths(data_dir=data_dir, database=data_dir / "cloudsync.sqlite3", log_dir=log_dir)

