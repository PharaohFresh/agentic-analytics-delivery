"""Generic verification harness for the agentic delivery pattern.

Loads declarative checks from checks.yml and runs each as a single-value
assertion (expected result: 0). Exit code 0 = all pass, 1 = any fail.

    python scripts/run_audit.py --demo     # in-memory SQLite fixture, no creds
    python scripts/run_audit.py            # real warehouse (implement connect())

The implemented checks target SQLite. To point this at a real warehouse,
adapt the SQL dialect and implement connect() for a read-only DB-API 2.0
connection; credentials come from the environment, never from this file.
"""
import argparse
import sqlite3
import sys

try:
    import yaml
except ImportError:
    sys.exit("[ERROR] pip install -r requirements.txt  (needs pyyaml)")

import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS_PATH = os.path.join(HERE, "checks.yml")

# Tiny fixture so the harness runs with no warehouse. Source tables and their
# fact-layer rebuilds are seeded to be consistent, so every check returns 0.
DEMO_FIXTURE = """
create table orders (order_id integer primary key);
insert into orders values (1), (2), (3);

create table order_items (
    id integer primary key, order_id integer, sale_price real
);
insert into order_items values
    (1, 1, 12.50), (2, 1,  9.00), (3, 2, 40.00),
    (4, 3,  5.25), (5, 3, 18.75);

-- fact layer: same grain as the sources
create table fct_orders as select order_id from orders;
create table fct_order_items as
    select id, order_id, sale_price from order_items;
"""


def demo_connection():
    conn = sqlite3.connect(":memory:")
    conn.executescript(DEMO_FIXTURE)
    conn.commit()
    return conn


def connect():
    """Return a DB-API 2.0 connection to your warehouse.

    Wire this to your warehouse client (e.g. the google-cloud-bigquery DB-API,
    snowflake-connector-python, or psycopg). Read credentials from the
    environment -- do not hard-code them here.
    """
    raise NotImplementedError(
        "Implement connect() for your warehouse, or run with --demo."
    )


def run_checks(conn):
    with open(CHECKS_PATH, encoding="utf-8") as f:
        checks = yaml.safe_load(f)["checks"]

    failures = 0
    cur = conn.cursor()
    for chk in checks:
        cur.execute(chk["sql"])
        value = cur.fetchone()[0]
        ok = value == 0
        status = "[OK]  " if ok else "[FAIL]"
        print(f"{status} {chk['label']}  (result={value})")
        if not ok:
            failures += 1

    print("-" * 60)
    if failures:
        print(f"[FAIL] {failures} check(s) failed.")
        return 1
    print("[OK] all checks passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo", action="store_true",
        help="run against an in-memory SQLite fixture (no warehouse needed)",
    )
    args = parser.parse_args()
    conn = demo_connection() if args.demo else connect()
    sys.exit(run_checks(conn))


if __name__ == "__main__":
    main()
