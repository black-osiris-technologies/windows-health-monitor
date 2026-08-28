from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = default or {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback.copy()
    return payload if isinstance(payload, dict) else fallback.copy()


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def append_runtime_error(path: Path, error: BaseException) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat()
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    with path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {details.rstrip()}\n")
