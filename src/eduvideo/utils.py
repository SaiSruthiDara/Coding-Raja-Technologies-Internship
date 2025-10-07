import os
import re
import uuid
from pathlib import Path


def ensure_dir(path: os.PathLike | str) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def safe_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or str(uuid.uuid4())


def unique_path(directory: str, stem: str, suffix: str) -> str:
    Path(directory).mkdir(parents=True, exist_ok=True)
    candidate = Path(directory) / f"{stem}{suffix}"
    if not candidate.exists():
        return str(candidate)
    for i in range(1, 10000):
        candidate = Path(directory) / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return str(candidate)
    raise RuntimeError("Could not find unique path")
