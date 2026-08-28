from __future__ import annotations

import json
import os
from datetime import datetime

from windows_health_monitor.crash_artifacts import (
    archive_memory_dump,
    discover_crash_artifacts,
    write_crash_inventory,
)


def test_discover_and_write_crash_inventory(tmp_path) -> None:
    memory_dump = tmp_path / "MEMORY.DMP"
    minidump_dir = tmp_path / "Minidump"
    minidump_dir.mkdir()
    memory_dump.write_bytes(b"memory")
    (minidump_dir / "one.dmp").write_bytes(b"mini")

    artifacts = discover_crash_artifacts(tmp_path)
    inventory = tmp_path / "inventory.json"
    write_crash_inventory(inventory, artifacts)

    payload = json.loads(inventory.read_text(encoding="utf-8"))
    assert {item["kind"] for item in payload["artifacts"]} == {"memory_dump", "minidump"}


def test_archive_memory_dump_is_idempotent_and_enforces_retention(tmp_path) -> None:
    source = tmp_path / "MEMORY.DMP"
    archive_dir = tmp_path / "archive"

    source.write_bytes(b"first")
    first = archive_memory_dump(source, archive_dir, retention=1)
    assert first is not None
    assert first.read_bytes() == b"first"
    assert archive_memory_dump(source, archive_dir, retention=1) == first

    source.write_bytes(b"second crash")
    later = datetime.now().timestamp() + 5
    os.utime(source, (later, later))
    second = archive_memory_dump(source, archive_dir, retention=1)

    assert second is not None
    assert second.read_bytes() == b"second crash"
    assert list(archive_dir.glob("MEMORY-*.dmp")) == [second]
