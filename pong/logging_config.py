"""Central logging setup for the project."""

from __future__ import annotations

import logging
import os
from typing import Literal


def configure_logging(mode: Literal["info", "debug"] = "info") -> None:
    level = logging.DEBUG if mode == "debug" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("pygame").setLevel(logging.WARNING)


def mode_from_env() -> Literal["info", "debug"]:
    return "debug" if os.environ.get("BATTLEPONG_DEBUG") else "info"
