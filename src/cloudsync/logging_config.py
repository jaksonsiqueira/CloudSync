"""Configuração centralizada de logs com rotação."""

import logging
from logging.handlers import RotatingFileHandler

from cloudsync.config import get_app_paths


def configure_logging(level: int = logging.INFO) -> None:
    paths = get_app_paths()
    handler = RotatingFileHandler(
        paths.log_dir / "cloudsync.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(existing, RotatingFileHandler) for existing in root.handlers):
        root.addHandler(handler)

