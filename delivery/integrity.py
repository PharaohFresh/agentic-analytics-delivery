from __future__ import annotations

import json
from pathlib import Path

from .catalog import DeliveryError, digest


def source_manifest(root: Path, files: list[str]) -> dict:
    base = root.resolve()
    records = []
    for relative in sorted(set(files)):
        path = (base / relative).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise DeliveryError("Manifest path escapes its source root.") from None
        data = path.read_bytes()
        records.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
    return {"algorithm": "sha256", "files": records}


def verify_manifest(root: Path, manifest: dict) -> None:
    current = source_manifest(root, [record["path"] for record in manifest["files"]])
    if current != manifest:
        raise DeliveryError("Source bytes changed, even if names or sizes stayed the same.")


def journal_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def verify_journal(path: Path, expected_tip: dict | None = None) -> dict:
    records = journal_records(path)
    previous = "0" * 64
    for sequence, record in enumerate(records, 1):
        body = {key: value for key, value in record.items() if key != "sha256"}
        if (body.get("sequence") != sequence or body.get("previous_sha256") != previous
                or record.get("sha256") != digest(body)):
            raise DeliveryError("Journal entry changed, disappeared or moved.")
        previous = record["sha256"]
    tip = {"event_count": len(records), "sha256": previous}
    if expected_tip is not None and tip != expected_tip:
        raise DeliveryError("Journal differs from the independently retained receipt tip.")
    return tip


def append_event(path: Path, event: str, payload: dict) -> dict:
    tip = verify_journal(path)
    body = {"sequence": tip["event_count"] + 1, "previous_sha256": tip["sha256"],
            "event": event, "payload": payload}
    record = {**body, "sha256": digest(body)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record
