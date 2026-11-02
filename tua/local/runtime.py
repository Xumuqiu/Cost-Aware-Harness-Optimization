"""Validate local, hash-locked Linux wheel bundles without network access."""

import hashlib
import json
from pathlib import Path

BUNDLES = Path(__file__).resolve().parent / ".runtime/bundles"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bundles(directory: Path = BUNDLES) -> dict:
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError("Offline runtime missing. Run: bash run-previous40.sh runtime-prepare")
    data = json.loads(manifest.read_text())
    for entry in data.values():
        path = directory / entry["archive"]
        if not path.is_file() or digest(path) != entry["sha256"]:
            raise ValueError(f"Offline runtime missing or checksum mismatch: {path}")
    return data
