from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .catalog import DeliveryError, approve_plan, audit_catalog, build_plan, digest
from .integrity import source_manifest, verify_manifest
from .workflow import execute, immutable_json, load, verify_receipt


FIXTURE = Path(__file__).parent / "fixtures/catalog.json"


def main(argv=None):
    parser=argparse.ArgumentParser(description="Audit lineage and execute an exact approved change against a synthetic local catalog.")
    sub=parser.add_subparsers(dest="command",required=True)
    d=sub.add_parser("demo");d.add_argument("--output",type=Path)
    a=sub.add_parser("audit");a.add_argument("catalog",type=Path)
    p=sub.add_parser("plan");p.add_argument("catalog",type=Path);p.add_argument("--output",required=True,type=Path)
    approval=sub.add_parser("approve");approval.add_argument("plan",type=Path);approval.add_argument("--actor",required=True);approval.add_argument("--output",required=True,type=Path)
    e=sub.add_parser("execute");e.add_argument("plan",type=Path);e.add_argument("--approval",required=True,type=Path);e.add_argument("--output",required=True,type=Path)
    v=sub.add_parser("verify");v.add_argument("output",type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="demo":
            root=args.output or Path("artifacts")/("delivery-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            root.mkdir(parents=True,exist_ok=False)
            catalog=load(FIXTURE);plan=build_plan(catalog)
            manifest=source_manifest(FIXTURE.parent,[FIXTURE.name]);verify_manifest(FIXTURE.parent,manifest)
            immutable_json(root/"source-manifest.json",manifest)
            immutable_json(root/"plan.json",plan)
            blocked=False
            try:execute(plan,{},root/"unapproved")
            except DeliveryError:blocked=True
            if not blocked:raise DeliveryError("Unapproved execution unexpectedly succeeded.")
            print("[BLOCKED AS EXPECTED] No approval: zero sandbox writes.")
            approval=approve_plan(plan,"synthetic-demo-reviewer")
            operation=plan["changes"][0]["operation_id"]
            clean=execute(plan,approval,root/"successful",failures_before={operation:2})
            interrupted=execute(plan,approval,root/"resumed",interrupt_after_write=True)
            resumed=execute(plan,approval,root/"resumed")
            rolled=execute(plan,approval,root/"rollback",corrupt_after=True)
            if clean["status"]!="verified" or interrupted["status"]!="interrupted" or resumed["status"]!="verified" or rolled["status"]!="rolled_back":
                raise DeliveryError("Expected delivery/recovery verdicts did not reproduce.")
            summary={"data_origin":"synthetic","unapproved_execution_blocked":blocked,
                     "initial_audit":audit_catalog(catalog),"retry_and_verify":clean,
                     "crash_window":interrupted,"checkpoint_recovery":resumed,"failed_verification":rolled}
            immutable_json(root/"demo-report.json",summary)
            print(f"[OK] {len(plan['initial_audit']['issues'])} environment leak; {len(plan['initial_audit']['affected_reports'])} affected report.")
            print("[OK] Two transient failures retried, written-but-uncheckpointed change recovered, failed verification restored.")
            print("Artifacts: "+str(root))
        elif args.command=="audit":
            report=audit_catalog(load(args.catalog));print(json.dumps(report,indent=2));return 0 if report["healthy"] else 1
        elif args.command=="plan":
            immutable_json(args.output,build_plan(load(args.catalog)));print("[OK] Exact repair plan written; no execution.")
        elif args.command=="approve":
            immutable_json(args.output,approve_plan(load(args.plan),args.actor));print("[OK] Local approval attestation written.")
        elif args.command=="execute":
            result=execute(load(args.plan),load(args.approval),args.output)
            print(json.dumps(result,indent=2))
            return 0 if result["status"]=="verified" else 1
        else:print(json.dumps(verify_receipt(args.output),indent=2))
    except (DeliveryError,OSError,ValueError,KeyError) as exc:
        print("[BLOCKED] "+str(exc));return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
