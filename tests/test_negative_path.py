"""Negative-path tests: prove the harness FAILS when the data is wrong.

A verification layer that has only ever been seen passing is a claim, not a
demonstration. Each test seeds one realistic defect into the clean demo
fixture and asserts run_checks exits non-zero with the right check tripping.

    python -m unittest discover -s tests -v
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
)

from run_audit import demo_connection, run_checks

GRAIN_ITEMS = "fct_order_items grain == order_items source rows"
GRAIN_ORDERS = "fct_orders grain == orders source rows"
ORPHANS = "no orphan order items (item without a parent order)"
NULL_PRICE = "no null sale_price in order items"
ITEM_KEYS = "order-item key coverage matches source"
ITEM_VALUES = "order-item values and parent mappings match source"
ORDER_KEYS = "order key coverage matches source"


def audit(conn):
    """Run the harness, returning (exit_code, sorted labels of failed checks)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = run_checks(conn)
    failed = [
        line.split("  (result=")[0].removeprefix("[FAIL] ")
        for line in buf.getvalue().splitlines()
        if line.startswith("[FAIL]") and "(result=" in line
    ]
    return code, sorted(failed)


class NegativePathTests(unittest.TestCase):
    def test_clean_fixture_passes(self):
        code, failed = audit(demo_connection())
        self.assertEqual(code, 0)
        self.assertEqual(failed, [])

    def test_orphan_item_is_caught(self):
        # A late-arriving item lands in source and fact, but its parent order
        # never did. Row counts still reconcile -- only the referential check
        # can see this one.
        conn = demo_connection()
        conn.execute("insert into order_items values (99, 42, 10.00)")
        conn.execute("insert into fct_order_items values (99, 42, 10.00)")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertEqual(failed, [ORPHANS])

    def test_null_sale_price_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set sale_price = null where id = 3")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertEqual(failed, sorted([NULL_PRICE, ITEM_VALUES]))

    def test_dropped_fact_rows_are_caught(self):
        # An incremental fact that silently lost a row: source-vs-fact
        # reconciliation is the only check positioned to notice.
        conn = demo_connection()
        conn.execute("delete from fct_order_items where id = 5")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertEqual(failed, sorted([GRAIN_ITEMS, ITEM_KEYS]))

    def test_dropped_parent_order_trips_count_key_and_relationship_checks(self):
        # Losing a parent order surfaces twice, independently: the order-grain
        # reconciliation breaks AND its items become orphans. Overlapping
        # checks are the point -- one defect, two alarms.
        conn = demo_connection()
        conn.execute("delete from fct_orders where order_id = 3")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertEqual(failed, sorted([GRAIN_ORDERS, ORDER_KEYS, ORPHANS]))

    def test_same_count_duplicate_key_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set id=2 where id=1")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertIn("no duplicate order-item keys", failed)
        self.assertNotIn(GRAIN_ITEMS, failed)

    def test_same_count_wrong_price_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set sale_price=sale_price+100 where id=1")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertEqual(failed, [ITEM_VALUES])

    def test_offsetting_price_errors_cannot_hide_behind_equal_totals(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set sale_price=sale_price+5 where id=1")
        conn.execute("update fct_order_items set sale_price=sale_price-5 where id=2")
        totals = conn.execute("select (select sum(sale_price) from order_items) - (select sum(sale_price) from fct_order_items)").fetchone()[0]
        self.assertEqual(totals, 0)
        self.assertEqual(audit(conn), (1, [ITEM_VALUES]))

    def test_wrong_but_existing_parent_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set order_id=3 where id=1")
        self.assertEqual(audit(conn), (1, [ITEM_VALUES]))

    def test_null_item_key_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_order_items set id=null where id=1")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertIn("no null order-item keys", failed)

    def test_same_count_duplicate_order_key_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_orders set order_id=2 where order_id=1")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertIn("no duplicate order keys", failed)

    def test_null_order_key_is_caught(self):
        conn = demo_connection()
        conn.execute("update fct_orders set order_id=null where order_id=1")
        code, failed = audit(conn)
        self.assertEqual(code, 1)
        self.assertIn("no null order keys", failed)


if __name__ == "__main__":
    unittest.main()
