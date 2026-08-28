from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .state import write_json_atomic


@dataclass(frozen=True)
class CrashArtifact:
    path: str
    kind: str
    size_bytes: int
    modified_at: str


def _describe(path: Path, kind: str) -> CrashArtifact | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return CrashArtifact(
        path=str(path),
        kind=kind,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
    )


def discover_crash_artifacts(windows_dir: Path | None = None) -> list[CrashArtifact]:
    root = windows_dir or Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates: list[tuple[Path, str]] = [(root / "MEMORY.DMP", "memory_dump")]
    candidates.extend((path, "minidump") for path in (root / "Minidump").glob("*.dmp"))
    candidates.extend(
        (path, "live_kernel_report")
        for path in (root / "LiveKernelReports").glob("**/*.dmp")
    )
    artifacts = [artifact for path, kind in candidates if (artifact := _describe(path, kind))]
    return sorted(artifacts, key=lambda item: item.modified_at, reverse=True)


def write_crash_inventory(path: Path, artifacts: list[CrashArtifact]) -> None:
    write_json_atomic(
        path,
        {
            "captured_at": datetime.now().astimezone().isoformat(),
            "artifacts": [asdict(artifact) for artifact in artifacts],
        },
    )


def archive_memory_dump(source: Path, archive_dir: Path, retention: int = 2) -> Path | None:
    if retention <= 0:
        raise ValueError("retention must be positive")
    artifact = _describe(source, "memory_dump")
    if artifact is None:
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)
    modified = datetime.fromisoformat(artifact.modified_at).strftime("%Y%m%d-%H%M%S")
    destination = archive_dir / f"MEMORY-{modified}-{artifact.size_bytes}.dmp"
    if not destination.exists():
        partial = destination.with_suffix(".dmp.partial")
        try:
            with source.open("rb") as input_file, partial.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file, length=16 * 1024 * 1024)
            shutil.copystat(source, partial)
            partial.replace(destination)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise

    archives = sorted(
        archive_dir.glob("MEMORY-*.dmp"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for expired in archives[retention:]:
        expired.unlink()
    return destination
