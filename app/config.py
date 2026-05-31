"""Runtime configuration."""

from __future__ import annotations

import os


def normalize_base_path(raw: str | None) -> str:
    if not raw or raw == "/":
        return ""
    path = raw.strip()
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/")


BASE_PATH = normalize_base_path(os.getenv("BASE_PATH", "/sudokuheist"))
