import copy
import json
from pathlib import Path

import pytest

from delivery.catalog import DeliveryError, approve_plan, audit_catalog, build_plan, digest, physical_references
from delivery.integrity import append_event, source_manifest, verify_journal, verify_manifest
from delivery.workflow import atomic_json, execute, load, verify_receipt
import delivery.workflow as workflow


FIXTURE=Path(__file__).resolve().parents[1]/"delivery/fixtures/catalog.json"


def catalog():return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("sql,expected",[
    ("WITH x AS (SELECT * FROM prod.orders) SELECT * FROM x",{"prod.orders"}),
    ("WITH x AS (SELECT * FROM prod.orders), y AS (SELECT * FROM x JOIN prod.items i USING(order_id)) SELECT * FROM y",{"prod.orders","prod.items"}),
    ("SELECT * FROM (SELECT * FROM prod.orders) a JOIN prod.customers c USING(customer_id)",{"prod.orders","prod.customers"}),
    ("SELECT * FROM `prod.orders` o -- JOIN dev.secret s ON 1=1\nWHERE o.status = 'FROM dev.not_a_table'",{"prod.orders"}),
    ("WITH orders AS (SELECT * FROM prod.real_orders) SELECT * FROM orders",{"prod.real_orders"}),
    ("SELECT 1 AS constant",set()),
])
def test_physical_lineage_understands_scope_aliases_and_comments(sql,expected):
    assert physical_references(sql)==expected


@pytest.mark.parametrize("sql",["DROP TABLE prod.orders","SELECT * FROM prod.orders; DELETE FROM prod.orders;","SELECT FROM"])
def test_nonquery_multistatement_or_unparseable_sql_is_rejected(sql):
    with pytest.raises(DeliveryError):physical_references(sql)


@pytest.mark.parametrize("sql",["SELECT * FROM EXTERNAL_QUERY('synthetic-connection', 'SELECT * FROM orders')",
                              "SELECT * FROM UNNEST([1, 2]) AS value"])
def test_external_and_table_valued_sources_need_explicit_lineage(sql):
    with pytest.raises(DeliveryError):physical_references(sql)


def test_environment_leak_reaches_downstream_report_and_declared_sources():
    report=audit_catalog(catalog())
    assert report["asset_count"]==8
    assert report["issues"]==[{"type":"environment_leak","asset":"prod.order_ingestion","reference":"dev.raw_orders"}]
    assert report["affected_reports"]==["prod.revenue_report"]
    assert report["declared_operational_sources"]["prod.revenue_report"]==["CRM","ERP"]
    assert "line_totals" not in report["edges"]["prod.daily_revenue"]


def test_missing_assets_and_cycles_are_not_reported_as_healthy():
    value=catalog();value["assets"][-1]["dependencies"].append("prod.missing")
    assert any(x["type"]=="missing_asset" for x in audit_catalog(value)["issues"])
    with pytest.raises(DeliveryError):build_plan(value)
    value=catalog();value["assets"][4]["dependencies"].append("prod.daily_revenue")
    assert any(x["type"]=="cycle" for x in audit_catalog(value)["issues"])
    with pytest.raises(DeliveryError):build_plan(value)


def test_duplicate_asset_identity_and_ambiguous_target_fail():
    value=catalog();value["assets"].append(copy.deepcopy(value["assets"][0]))
    with pytest.raises(DeliveryError):audit_catalog(value)
    value=catalog();other=copy.deepcopy(value["assets"][1]);other["id"]="prod.another_raw_orders";value["assets"].append(other)
    with pytest.raises(DeliveryError,match="unique"):build_plan(value)


def test_sql_reference_repairs_are_not_inferred_from_string_replacement():
    value=catalog();value["assets"][5]["sql"]="SELECT * FROM dev.raw_orders"
    with pytest.raises(DeliveryError,match="SQL reference"):build_plan(value)


def test_unapproved_or_altered_plan_cannot_write(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer")
    with pytest.raises(DeliveryError):execute(plan,{},tmp_path/"unapproved")
    assert not (tmp_path/"unapproved").exists()
    changed=copy.deepcopy(plan);changed["changes"][0]["after"]="dev.raw_orders"
    with pytest.raises(DeliveryError):execute(changed,approval,tmp_path/"changed")
    prod=copy.deepcopy(plan);prod["target"]="live_production"
    with pytest.raises(DeliveryError):execute(prod,approval,tmp_path/"prod")


def test_successful_delivery_has_independent_readback_and_no_repeated_effect(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer")
    root=tmp_path/"run";receipt=execute(plan,approval,root)
    assert receipt["status"]=="verified" and receipt["final_audit"]["healthy"]
    assert receipt["completed_operations"]==1
    journal=(root/"journal.jsonl").read_bytes()
    assert execute(plan,approval,root)==receipt
    assert (root/"journal.jsonl").read_bytes()==journal


def test_bounded_failure_then_exact_plan_resume(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer");op=plan["changes"][0]["operation_id"]
    root=tmp_path/"run"
    result=execute(plan,approval,root,failures_before={op:20},max_attempts=3)
    assert result["status"]=="partial" and result["attempts"][op]==3
    assert load(root/"catalog.json")==plan["before"]
    assert execute(plan,approval,root)["status"]=="verified"


def test_two_transient_failures_then_success_is_three_attempts(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer");op=plan["changes"][0]["operation_id"]
    result=execute(plan,approval,tmp_path/"run",failures_before={op:2})
    assert result["attempts_this_execution"][op]==3


def test_crash_after_write_before_checkpoint_recovers_from_exact_writeahead_record(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer");root=tmp_path/"run"
    assert execute(plan,approval,root,interrupt_after_write=True)["status"]=="interrupted"
    result=execute(plan,approval,root)
    assert result["status"]=="verified"
    events=[json.loads(line)["event"] for line in (root/"journal.jsonl").read_text().splitlines()]
    assert "operation_recovered" in events and "operation_applied" not in events


@pytest.mark.parametrize('window', ['after_applied', 'after_recovered'])
def test_crash_before_either_checkpoint_write_can_resume(tmp_path,monkeypatch,window):
    plan=build_plan(catalog());approval=approve_plan(plan,'test-reviewer');root=tmp_path/'run'
    if window=='after_recovered':
        execute(plan,approval,root,interrupt_after_write=True)
    original=workflow.atomic_json
    def crash_on_checkpoint(path,value):
        if path.name=='checkpoint.json':
            raise OSError('injected crash before durable checkpoint')
        return original(path,value)
    with monkeypatch.context() as context:
        context.setattr(workflow,'atomic_json',crash_on_checkpoint)
        with pytest.raises(OSError,match='injected crash'):
            execute(plan,approval,root)
    result=execute(plan,approval,root)
    assert result['status']=='verified'
    events=[json.loads(line)['event'] for line in (root/'journal.jsonl').read_text().splitlines()]
    assert events.count('operation_started')==1
    assert events.count('operation_recovered')==(2 if window=='after_recovered' else 1)


def test_unrelated_state_drift_in_crash_window_is_not_accepted(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer");root=tmp_path/"run"
    execute(plan,approval,root,interrupt_after_write=True)
    current=load(root/"catalog.json");current["assets"][0]["logical_name"]="unapproved-change";atomic_json(root/"catalog.json",current)
    with pytest.raises(DeliveryError,match="drifted"):execute(plan,approval,root)


def test_failed_verification_restores_working_fixture_and_keeps_candidate_evidence(tmp_path):
    plan=build_plan(catalog());approval=approve_plan(plan,"test-reviewer");root=tmp_path/"run"
    result=execute(plan,approval,root,corrupt_after=True)
    assert result["status"]=="rolled_back"
    assert load(root/"catalog.json")==plan["before"]
    assert list(root.glob("failed-catalog-*.json"))
    assert not (root/"verified-receipt.json").exists()
    assert execute(plan,approval,root)["status"]=="verified"


@pytest.mark.parametrize("change",["edit","truncate","reorder","append"])
def test_journal_tampering_is_detected_against_retained_receipt(tmp_path,change):
    plan=build_plan(catalog());root=tmp_path/"run";execute(plan,approve_plan(plan,"test"),root)
    path=root/"journal.jsonl";lines=path.read_text().splitlines()
    if change=="edit":entry=json.loads(lines[1]);entry["payload"]["attempt"]=99;lines[1]=json.dumps(entry)
    elif change=="truncate":lines=lines[:-1]
    elif change=="reorder":lines[0],lines[1]=lines[1],lines[0]
    else:append_event(path,"unapproved-extra-event",{});lines=path.read_text().splitlines()
    path.write_text("\n".join(lines)+"\n")
    with pytest.raises(DeliveryError):verify_receipt(root)


def test_source_manifest_checks_content_not_only_size_and_rejects_path_escape(tmp_path):
    (tmp_path/"source.txt").write_text("alpha")
    manifest=source_manifest(tmp_path,["source.txt"]);verify_manifest(tmp_path,manifest)
    (tmp_path/"source.txt").write_text("bravo")
    with pytest.raises(DeliveryError):verify_manifest(tmp_path,manifest)
    with pytest.raises(DeliveryError):source_manifest(tmp_path,["../outside.txt"])
