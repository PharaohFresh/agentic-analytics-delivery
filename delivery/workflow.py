from __future__ import annotations

import json
from pathlib import Path

from .catalog import DeliveryError, audit_catalog, catalog_after, digest, indexed_assets, validate_plan
from .integrity import append_event, journal_records, verify_journal


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def immutable_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise DeliveryError("Previously saved evidence changed.")
    else:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def execute(plan, approval, root: Path, *, failures_before=None, interrupt_after_write=False,
            corrupt_after=False, max_attempts=3) -> dict:
    plan_hash = validate_plan(plan)
    if not isinstance(approval, dict) or approval.get("plan_sha256") != plan_hash or not approval.get("approver"):
        raise DeliveryError("No approval covers this exact plan.")
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not 1 <= max_attempts <= 10:
        raise DeliveryError("Retry bound must be an integer from one to ten.")
    root.mkdir(parents=True, exist_ok=True)
    catalog_path, checkpoint_path = root / "catalog.json", root / "checkpoint.json"
    journal_path, receipt_path = root / "journal.jsonl", root / "verified-receipt.json"
    immutable_json(root / "approved-plan.json", plan)
    immutable_json(root / "approval.json", approval)
    immutable_json(root / "before-catalog.json", plan["before"])
    if receipt_path.exists():
        return verify_receipt(root)
    if not catalog_path.exists():
        atomic_json(catalog_path, plan["before"])
    checkpoint = load(checkpoint_path) if checkpoint_path.exists() else {"plan_sha256": plan_hash, "completed": []}
    if checkpoint.get("plan_sha256") != plan_hash:
        raise DeliveryError("Checkpoint belongs to a different approved plan.")
    completed = set(checkpoint["completed"])
    verify_journal(journal_path)
    current = load(catalog_path)
    expected = catalog_after(plan, completed)
    if current != expected:
        pending = [change for change in plan["changes"] if change["operation_id"] not in completed]
        last = journal_records(journal_path)[-1] if journal_records(journal_path) else None
        recover = (pending and last and last["event"] in {"operation_started", "operation_applied", "operation_recovered"}
                   and last["payload"].get("plan_sha256") == plan_hash
                   and last["payload"].get("operation_id") == pending[0]["operation_id"])
        if recover and last["event"] == "operation_started":
            recover = last["payload"].get("before_sha256") == digest(expected)
        if recover and last["event"] == "operation_applied":
            recover = last["payload"].get("after_sha256") == digest(current)
        if not recover or current != catalog_after(plan, completed | {pending[0]["operation_id"]}):
            raise DeliveryError("Working state drifted outside the approved checkpoint.")
        completed.add(pending[0]["operation_id"])
        append_event(journal_path, "operation_recovered", {"plan_sha256": plan_hash, "operation_id": pending[0]["operation_id"]})
        atomic_json(checkpoint_path, {"plan_sha256": plan_hash, "completed": sorted(completed)})
    if not journal_records(journal_path):
        append_event(journal_path, "approval_checked", {"plan_sha256": plan_hash, "approver": approval["approver"]})
    remaining_failures = dict(failures_before or {})
    attempts = {}
    for change in plan["changes"]:
        operation_id = change["operation_id"]
        if operation_id in completed:
            continue
        for attempt in range(1, max_attempts + 1):
            attempts[operation_id] = attempt
            append_event(journal_path, "operation_started", {"plan_sha256": plan_hash, "operation_id": operation_id,
                                                           "before_sha256": digest(load(catalog_path)), "attempt": attempt})
            if remaining_failures.get(operation_id, 0):
                remaining_failures[operation_id] -= 1
                append_event(journal_path, "retryable_failure", {"operation_id": operation_id, "attempt": attempt})
                if attempt == max_attempts:
                    return {"status": "partial", "completed_operations": len(completed), "attempts": attempts,
                            "plan_sha256": plan_hash, "journal_tip": verify_journal(journal_path)}
                continue
            candidate = catalog_after(plan, completed | {operation_id})
            atomic_json(catalog_path, candidate)
            if interrupt_after_write:
                # A deliberate crash window: write occurred, checkpoint did not.
                return {"status": "interrupted", "completed_operations": len(completed),
                        "plan_sha256": plan_hash, "journal_tip": verify_journal(journal_path)}
            if load(catalog_path) != candidate:
                raise DeliveryError("Operation readback failed.")
            completed.add(operation_id)
            append_event(journal_path, "operation_applied", {"plan_sha256": plan_hash, "operation_id": operation_id, "after_sha256": digest(candidate)})
            atomic_json(checkpoint_path, {"plan_sha256": plan_hash, "completed": sorted(completed)})
            break
    if corrupt_after:
        corrupted = load(catalog_path)
        corrupted["assets"][0]["logical_name"] += "-injected-drift"
        atomic_json(catalog_path, corrupted)
    final = load(catalog_path)
    audit = audit_catalog(final)
    if digest(final) != plan["expected_after_sha256"] or not audit["healthy"]:
        failed_hash = digest(final)
        immutable_json(root / ("failed-catalog-" + failed_hash[:12] + ".json"), final)
        append_event(journal_path, "verification_failed", {"candidate_sha256": failed_hash})
        atomic_json(catalog_path, plan["before"])
        atomic_json(checkpoint_path, {"plan_sha256": plan_hash, "completed": []})
        append_event(journal_path, "working_fixture_restored", {"catalog_sha256": digest(load(catalog_path))})
        return {"status": "rolled_back", "failed_candidate_sha256": failed_hash,
                "restored_sha256": digest(load(catalog_path)), "plan_sha256": plan_hash,
                "journal_tip": verify_journal(journal_path)}
    append_event(journal_path, "independent_readback_passed", {"catalog_sha256": digest(final), "healthy": audit["healthy"]})
    receipt = {"status": "verified", "target": "local synthetic files only", "data_origin": "synthetic",
               "plan_sha256": plan_hash, "before_sha256": plan["before_sha256"], "after_sha256": digest(final),
               "completed_operations": len(completed), "attempts_this_execution": attempts,
               "final_audit": audit, "journal_tip": verify_journal(journal_path),
               "cloud_mutations": 0, "identity_authentication": "not implemented; local approval attestation"}
    immutable_json(receipt_path, receipt)
    return verify_receipt(root)


def verify_receipt(root: Path) -> dict:
    receipt = load(root / "verified-receipt.json")
    catalog = load(root / "catalog.json")
    if digest(catalog) != receipt["after_sha256"] or not audit_catalog(catalog)["healthy"]:
        raise DeliveryError("Catalog differs from the independently retained verification receipt.")
    verify_journal(root / "journal.jsonl", receipt["journal_tip"])
    return receipt
