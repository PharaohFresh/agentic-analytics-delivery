from __future__ import annotations

import copy
import hashlib
import json

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope


class DeliveryError(ValueError):
    pass


def digest(value) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def physical_references(sql: str) -> set[str]:
    try:
        parsed = sqlglot.parse(sql, read="bigquery")
        if len(parsed) != 1 or not isinstance(parsed[0], exp.Query):
            raise DeliveryError("Only one static query definition is supported.")
        references = set()
        for scope in traverse_scope(parsed[0]):
            if scope.is_udtf:
                raise DeliveryError("Table-valued functions require explicitly supplied lineage.")
            for _, source in scope.selected_sources.values():
                if isinstance(source, exp.Table):
                    if not isinstance(source.this, exp.Identifier):
                        raise DeliveryError("External or computed table references require explicit lineage.")
                    references.add(".".join(part.name for part in source.parts))
        return references
    except sqlglot.errors.SqlglotError as exc:
        raise DeliveryError("SQL dependency parsing failed.") from exc


def indexed_assets(catalog: dict) -> dict:
    if not isinstance(catalog, dict) or catalog.get("version") != 1 or not isinstance(catalog.get("assets"), list):
        raise DeliveryError("Unsupported catalog contract.")
    assets = {}
    for asset in catalog["assets"]:
        if (not isinstance(asset, dict) or not isinstance(asset.get("id"), str) or not asset["id"]
                or asset.get("environment") not in {"dev", "prod"}
                or asset.get("kind") not in {"source", "table", "view", "pipeline", "report"}
                or not isinstance(asset.get("logical_name"), str) or not asset["logical_name"]):
            raise DeliveryError("Invalid asset identity, environment, kind or logical name.")
        if asset["id"] in assets:
            raise DeliveryError("Duplicate asset identity.")
        dependencies = asset.get("dependencies", [])
        if (not isinstance(dependencies, list) or any(not isinstance(x, str) or not x for x in dependencies)
                or len(dependencies) != len(set(dependencies))):
            raise DeliveryError("Dependencies must be distinct nonempty asset IDs.")
        if asset["kind"] == "view" and not isinstance(asset.get("sql"), str):
            raise DeliveryError("View definitions require SQL text.")
        assets[asset["id"]] = asset
    return assets


def audit_catalog(catalog: dict) -> dict:
    assets = indexed_assets(catalog)
    edges, issues = {}, []
    for asset_id, asset in assets.items():
        references = set(asset.get("dependencies", []))
        if asset["kind"] == "view":
            try:
                references.update(physical_references(asset["sql"]))
            except DeliveryError as exc:
                issues.append({"type": "unparsed_sql", "asset": asset_id, "detail": str(exc)})
        edges[asset_id] = sorted(references)
        for reference in sorted(references):
            if reference not in assets:
                issues.append({"type": "missing_asset", "asset": asset_id, "reference": reference})
            elif asset["environment"] == "prod" and assets[reference]["environment"] != "prod":
                issues.append({"type": "environment_leak", "asset": asset_id, "reference": reference})
    state, stack, cycles = {}, [], set()

    def visit(node):
        if state.get(node) == 1:
            cycle = stack[stack.index(node):]
            canonical = min(tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle)))
            cycles.add(canonical)
            return
        if state.get(node) == 2 or node not in assets:
            return
        state[node] = 1
        stack.append(node)
        for child in edges[node]:
            visit(child)
        stack.pop()
        state[node] = 2

    for node in sorted(assets):
        visit(node)
    for cycle in sorted(cycles):
        issues.append({"type": "cycle", "path": list(cycle) + [cycle[0]]})

    def descendants(node):
        seen, pending = set(), [node]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(edges.get(current, []))
        return seen

    affected = set()
    sources = {}
    for asset_id, asset in assets.items():
        reachable = descendants(asset_id)
        if asset["kind"] == "report":
            if any(issue.get("asset") in reachable or any(x in reachable for x in issue.get("path", [])) for issue in issues):
                affected.add(asset_id)
            sources[asset_id] = sorted({assets[node]["operational_source"] for node in reachable
                                        if node in assets and assets[node].get("operational_source")})
    return {"asset_count": len(assets), "edges": edges, "issues": issues,
            "affected_reports": sorted(affected), "declared_operational_sources": sources,
            "healthy": not issues, "evidence": "parsed SQL and declared synthetic metadata; no live-system verification"}


def build_plan(catalog: dict) -> dict:
    audit = audit_catalog(catalog)
    if any(issue["type"] != "environment_leak" for issue in audit["issues"]):
        raise DeliveryError("Unresolved SQL, missing assets or cycles need review before automatic repair planning.")
    assets = indexed_assets(catalog)
    changes = []
    after = copy.deepcopy(catalog)
    after_assets = indexed_assets(after)
    for issue in audit["issues"]:
        asset = assets[issue["asset"]]
        before = assets[issue["reference"]]
        if issue["reference"] not in asset.get("dependencies", []):
            raise DeliveryError("A SQL reference requires an explicitly reviewed SQL change; it is not rewritten heuristically.")
        candidates = [x["id"] for x in assets.values() if x["environment"] == "prod"
                      and x["kind"] == before["kind"] and x["logical_name"] == before["logical_name"]]
        if len(candidates) != 1:
            raise DeliveryError("The source has no unique production counterpart.")
        index = asset["dependencies"].index(issue["reference"])
        change = {"asset": issue["asset"], "dependency_index": index,
                  "before": issue["reference"], "after": candidates[0]}
        change["operation_id"] = digest(change)
        changes.append(change)
        after_assets[issue["asset"]]["dependencies"][index] = candidates[0]
    if not audit_catalog(after)["healthy"]:
        raise DeliveryError("Proposed repair does not satisfy the independent catalog audit.")
    return {"version": 1, "target": "local_synthetic_fixture", "before": copy.deepcopy(catalog),
            "before_sha256": digest(catalog), "changes": changes, "expected_after_sha256": digest(after),
            "initial_audit": audit, "data_origin": "synthetic"}


def validate_plan(plan: dict) -> str:
    if not isinstance(plan, dict) or plan.get("target") != "local_synthetic_fixture":
        raise DeliveryError("Only the local synthetic fixture target is supported.")
    if plan != build_plan(plan["before"]):
        raise DeliveryError("The plan changed or contains unverified operations.")
    return digest(plan)


def approve_plan(plan: dict, actor: str) -> dict:
    if not actor.strip():
        raise DeliveryError("An explicit approver label is required.")
    return {"plan_sha256": validate_plan(plan), "approver": actor,
            "authorization_type": "local-file attestation; not authenticated production identity"}


def catalog_after(plan: dict, completed: set[str]) -> dict:
    value = copy.deepcopy(plan["before"])
    assets = indexed_assets(value)
    operation_ids = {change["operation_id"] for change in plan["changes"]}
    if completed - operation_ids:
        raise DeliveryError("Checkpoint contains an operation outside the plan.")
    for change in plan["changes"]:
        if change["operation_id"] in completed:
            assets[change["asset"]]["dependencies"][change["dependency_index"]] = change["after"]
    return value
