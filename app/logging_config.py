"""Minimal application logging setup."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure readable line-oriented logs once for the process."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )

