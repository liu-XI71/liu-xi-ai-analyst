"""Behavioral tests for temporal, monetary, and evidence contracts."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.domains import repurchase as rp


class RepurchaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "retail.sqlite3"
        rp.build_database(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def run_request(self, **kwargs):
        return rp.analyze({"task": "report", "start": "2026-03-01", "end": "2026-05-31", **kwargs}, self.path)

    def fixture_orders(self):
        customers = [("A", "华东"), ("B", "华南"), ("C", "华东"), ("D", "西部"), ("E", "华东")]
        dates = [("A", "2026-01-01", 10000), ("A", "2026-01-01", 2000), ("A", "2026-01-08", 3000), ("A", "2026-01-31", 4000), ("A", "2026-02-01", 5000), ("B", "2026-06-25", 10000), ("B", "2026-06-30", 5000), ("C", "2026-05-31", 20000), ("C", "2026-06-07", 6000), ("C", "2026-06-30", 7000), ("D", "2026-03-01", 8000), ("E", "2026-02-01", 9000), ("E", "2026-02-03", 1000)]
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM repurchase_orders")
            conn.execute("DELETE FROM repurchase_customers")
            conn.executemany("INSERT INTO repurchase_customers VALUES (?,?)", customers)
            conn.executemany("INSERT INTO repurchase_orders VALUES (?,?,?,?)", [(str(i), *row) for i, row in enumerate(dates)])

    @staticmethod
    def evidence(result, eid):
        return next(item for item in result["evidence"] if item["id"] == eid)

    @staticmethod
    def table(result, tid):
        return next(item for item in result["tables"] if item["id"] == tid)["rows"]

    def test_generation_reproducible_and_idempotent(self):
        other = Path(self.temp.name) / "other.sqlite3"
        rp.build_database(other)
        def rows(path):
            with sqlite3.connect(path) as conn:
                return conn.execute("SELECT * FROM repurchase_orders ORDER BY order_id").fetchall()
        expected = rows(self.path)
        self.assertEqual(expected, rows(other))
        rp.build_database(self.path)
        self.assertEqual(expected, rows(self.path))
        self.assertGreater(len(expected), 1200)

    def test_same_day_excluded_and_d7_d30_boundaries_included(self):
        self.fixture_orders()
        result = self.run_request(task="diagnose", start="2026-01-01", end="2026-01-01")
        row = self.evidence(result, "rp-cohort")["rows"][0]
        self.assertEqual((row["customers"], row["mature7"], row["repeat7"], row["repeat30"]), (1, 1, 1, 1))
        self.assertEqual(row["value30_cents"], 15000)  # D0–D29, excludes D30 transaction
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM repurchase_orders WHERE customer_id='A' AND order_date>'2026-01-01'")
        row = self.evidence(self.run_request(task="diagnose", start="2026-01-01", end="2026-01-01"), "rp-cohort")["rows"][0]
        self.assertEqual((row["repeat7"], row["repeat30"]), (0, 0))

    def test_immature_customers_excluded_even_if_already_repeated(self):
        self.fixture_orders()
        result = self.run_request(task="diagnose", start="2026-06-25", end="2026-06-30")
        row = self.evidence(result, "rp-cohort")["rows"][0]
        self.assertEqual((row["customers"], row["mature7"], row["repeat7"], row["mature30"]), (1, 0, 0, 0))
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(next(k for k in result["kpis"] if k["id"] == "repeat7")["value"])

    def test_exact_30_day_maturity_included(self):
        self.fixture_orders()
        row = self.evidence(self.run_request(task="diagnose", start="2026-05-31", end="2026-05-31"), "rp-cohort")["rows"][0]
        self.assertEqual((row["mature7"], row["repeat7"], row["mature30"], row["repeat30"], row["value30_cents"]), (1, 1, 1, 1, 26000))

    def test_candidate_features_never_read_future_orders(self):
        self.fixture_orders()
        args = {"task": "segment", "start": "2026-01-01", "end": "2026-03-31", "filters": {"budget": 100, "segment": "all"}}
        before = self.run_request(**args)
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO repurchase_orders VALUES ('future','E','2026-06-15',99999999)")
        after = self.run_request(**args)
        self.assertEqual(self.table(before, "rp-candidates-table"), self.table(after, "rp-candidates-table"))
        self.assertEqual(self.table(before, "rp-segments-table"), self.table(after, "rp-segments-table"))

    def test_start_changes_monetary_window_and_end_changes_rfm(self):
        self.fixture_orders()
        a = self.run_request(task="segment", start="2026-01-01", end="2026-03-31")
        b = self.run_request(task="segment", start="2026-03-01", end="2026-03-31")
        self.assertGreater(sum(r["window_value"] for r in self.table(a, "rp-segments-table")), sum(r["window_value"] for r in self.table(b, "rp-segments-table")))
        c = self.run_request(task="segment", start="2026-01-01", end="2026-02-04")
        self.assertNotEqual(self.table(a, "rp-segments-table"), self.table(c, "rp-segments-table"))

    def test_budget_allocation_is_reproducible_and_does_not_overspend(self):
        args = {"filters": {"budget": 17.55, "contact_cost": 1.25, "holdout_ratio": 0.3, "seed": "test", "limit": 100}}
        first, second = self.run_request(**args), self.run_request(**args)
        candidates = self.table(first, "rp-candidates-table")
        self.assertEqual(candidates, self.table(second, "rp-candidates-table"))
        self.assertLessEqual(sum(round(row["planned_cost"] * 100) for row in candidates), 1755)
        self.assertGreater(first["metric_contract"]["allocation"]["holdout_n"], 0)
        changed = self.run_request(filters={**args["filters"], "seed": "other"})
        self.assertEqual([r["customer_id"] for r in candidates], [r["customer_id"] for r in self.table(changed, "rp-candidates-table")])
        self.assertNotEqual([r["assignment"] for r in candidates], [r["assignment"] for r in self.table(changed, "rp-candidates-table")])

    def test_zero_budget_produces_no_actions(self):
        result = self.run_request(task="segment", filters={"budget": 0})
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(self.table(result, "rp-candidates-table"), [])
        self.assertEqual(result["metric_contract"]["allocation"]["planned_cost"], 0)

    def test_region_filter_is_real_and_empty_results_have_null_rates(self):
        self.fixture_orders()
        result = self.run_request(task="diagnose", start="2026-01-01", end="2026-06-30", filters={"region": "华东"})
        self.assertEqual(self.evidence(result, "rp-cohort")["rows"][0]["customers"], 3)
        empty = self.run_request(task="diagnose", filters={"region": "华北"})
        self.assertEqual(empty["status"], "insufficient_data")
        self.assertEqual(next(k for k in empty["kpis"] if k["id"] == "customers")["value"], 0)
        self.assertIsNone(next(k for k in empty["kpis"] if k["id"] == "repeat30")["value"])

    def test_invalid_inputs_request_clarification_instead_of_ignoring(self):
        invalid = [{"start": "2026-13-01"}, {"start": ""}, {"start": "2026-06-01", "end": "2026-03-01"}, {"end": "2027-01-01"}, {"compare_start": "2026-01-01"}, {"task": "experiment"}, {"filters": {"budget": -1}}, {"filters": {"contact_cost": 0}}, {"filters": {"holdout_ratio": float("nan")}}, {"filters": {"limit": 4.5}}, {"filters": {"unregistered": 1}}, {"filters": {"region": "not-a-region"}}, {"task": "diagnose", "filters": {"segment": "cooling"}}]
        invalid.extend([{"filters": []}, {"compare_start": "", "compare_end": ""}, {"filters": {"budget": "NaN"}}])
        for patch in invalid:
            with self.subTest(patch=patch):
                result = self.run_request(**patch)
                self.assertEqual(result["status"], "needs_clarification")
                self.assertEqual(result["evidence"], [])

    def test_comparison_window_is_executed(self):
        self.fixture_orders()
        result = self.run_request(task="diagnose", start="2026-03-01", end="2026-05-31", compare_start="2026-01-01", compare_end="2026-02-28")
        compare = self.evidence(result, "rp-compare")
        self.assertEqual(compare["parameters"]["start"], "2026-01-01")
        self.assertEqual(compare["rows"][0]["customers"], 2)
        self.assertEqual(next(k for k in result["kpis"] if k["id"] == "customers")["previous"], 2)

    def test_all_evidence_sql_replays_to_exact_reported_rows(self):
        result = self.run_request(filters={"budget": 1, "contact_cost": 0.6, "holdout_ratio": 0.2})
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            for evidence in result["evidence"]:
                actual = [dict(row) for row in conn.execute(evidence["sql"], evidence["parameters"])]
                self.assertEqual(actual, evidence["rows"], evidence["id"])
        ids = {e["id"] for e in result["evidence"]}
        for finding in result["findings"]:
            self.assertTrue(set(finding["evidence_ids"]) <= ids)


if __name__ == "__main__":
    unittest.main()
