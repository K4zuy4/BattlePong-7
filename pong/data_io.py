"""Tiny JSON helper for loading/saving local data files with defaults."""

from __future__ import annotations

import json
import os
from typing import Any
import logging

logger = logging.getLogger(__name__)


def load_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        logger.debug("load_json missing file, returning default", extra={"path": path})
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("load_json failed, returning default", extra={"path": path, "error": str(exc)})
        return default


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.debug("save_json wrote file", extra={"path": path})
