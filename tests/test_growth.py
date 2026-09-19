"""Behavioral tests for growth business contracts, evidence, and statistics."""
import json
import math
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.domains import growth


class GrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.db = Path(cls.directory.name) / "growth.sqlite"
        growth.build_database(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_dataset_is_reproducible_and_idempotent_without_other_table_loss(self):
        other = Path(self.directory.name) / "repeated.sqlite"
        growth.build_database(other)
        with sqlite3.connect(other) as con:
            con.execute("CREATE TABLE IF NOT EXISTS other_domain (value TEXT)")
            con.execute("INSERT INTO other_domain VALUES ('preserve')")
        growth.build_database(other)
        with sqlite3.connect(self.db) as original, sqlite3.connect(other) as repeated:
            self.assertEqual(original.execute("SELECT * FROM growth_users ORDER BY user_id").fetchall(), repeated.execute("SELECT * FROM growth_users ORDER BY user_id").fetchall())
            self.assertEqual(original.execute("SELECT * FROM growth_activity ORDER BY user_id, activity_date").fetchall(), repeated.execute("SELECT * FROM growth_activity ORDER BY user_id, activity_date").fetchall())
            self.assertEqual(repeated.execute("SELECT value FROM other_domain").fetchone()[0], "preserve")

    def test_retention_agrees_with_independent_user_event_count(self):
        result = growth.analyze({}, self.db)
        current = next(row for row in result["tables"][0]["rows"] if row["period"] == "current")
        with sqlite3.connect(self.db) as con:
            users = dict(con.execute("SELECT user_id, signup_date FROM growth_users WHERE signup_date BETWEEN '2026-08-24' AND '2026-08-30'"))
            all_activity = con.execute("SELECT user_id, activity_date FROM growth_activity").fetchall()
        retained = set()
        exact_d7 = set()
        for uid, event_date in all_activity:
            if uid not in users:
                continue
            offset = (date.fromisoformat(event_date) - date.fromisoformat(users[uid])).days
            if 1 <= offset <= 7:
                retained.add(uid)
            if offset == 7:
                exact_d7.add(uid)
        self.assertEqual(current["users"], len(users))
        self.assertEqual(current["retained_users"], len(retained))
        self.assertGreater(len(retained), len(exact_d7))
        self.assertLess(len(retained), len(users))  # Signup-day activity never implies retention.

    def test_symmetric_decomposition_reconciles_and_reverses(self):
        previous = [{"channel": "organic", "device": "web", "users": 100, "retained_users": 50}, {"channel": "social", "device": "web", "users": 100, "retained_users": 10}]
        current = [{"channel": "organic", "device": "web", "users": 50, "retained_users": 30}, {"channel": "social", "device": "web", "users": 150, "retained_users": 30}]
        rows = growth.symmetric_decomposition(previous, current)
        self.assertAlmostEqual(sum(row["total_pp"] for row in rows), 0)
        self.assertAlmostEqual(sum(row["mix_pp"] for row in rows), -10)
        self.assertAlmostEqual(sum(row["performance_pp"] for row in rows), 10)
        reverse = growth.symmetric_decomposition(current, previous)
        self.assertAlmostEqual(sum(row["mix_pp"] for row in reverse), 10)
        self.assertAlmostEqual(sum(row["performance_pp"] for row in reverse), -10)

    def test_new_stratum_is_mix_not_invented_performance(self):
        previous = [{"channel": "organic", "device": "web", "users": 100, "retained_users": 50}]
        current = previous + [{"channel": "social", "device": "web", "users": 100, "retained_users": 20}]
        rows = growth.symmetric_decomposition(previous, current)
        self.assertAlmostEqual(sum(row["total_pp"] for row in rows), -15)
        new = next(row for row in rows if row["channel"] == "social")
        self.assertIsNone(new["previous_rate_pct"])
        self.assertEqual(new["performance_pp"], 0)

    def test_filters_change_the_population_and_are_parameterized(self):
        result = growth.analyze({"filters": {"channel": ["paid_search"], "device": "android"}}, self.db)
        self.assertEqual(result["status"], "completed")
        strata = next(e for e in result["evidence"] if e["id"] == "growth-strata")
        self.assertTrue(all(row["channel"] == "paid_search" and row["device"] == "android" for row in strata["rows"]))
        self.assertIn(":filter_channel_0", strata["sql"])
        self.assertNotIn("paid_search", strata["sql"])
        self.assertEqual(strata["parameters"]["filter_channel_0"], "paid_search")

    def test_malformed_and_unsupported_inputs_request_clarification(self):
        cases = [
            {"task": "delete"}, {"start": "2026-02-30", "end": "2026-08-30"},
            {"start": "2026-08-30"}, {"start": "2026-08-30", "end": "2026-08-01"},
            {"compare_start": "2026-08-17"}, {"filters": []},
            {"filters": {"country": "CN"}}, {"filters": {"channel": "' OR 1=1--"}},
            {"filters": {"device": []}}, {"task": "experiment", "compare_start": "2026-08-01", "compare_end": "2026-08-07"},
            {"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-24", "compare_end": "2026-08-25"},
        ]
        for request in cases:
            with self.subTest(request=request):
                result = growth.analyze(request, self.db)
                self.assertEqual(result["status"], "needs_clarification")
                self.assertIn("clarification", result)
                self.assertEqual(result["kpis"], [])

    def test_immature_and_missing_periods_never_silently_truncate(self):
        for request in [
            {"start": "2026-08-31", "end": "2026-09-06"},
            {"start": "2026-08-24", "end": "2026-08-31"},
            {"start": "2026-07-01", "end": "2026-07-20"},
            {"start": "2025-08-01", "end": "2025-08-07"},
        ]:
            with self.subTest(request=request):
                result = growth.analyze(request, self.db)
                self.assertEqual(result["status"], "insufficient_data")
                self.assertEqual(result["kpis"], [])

    def test_empty_population_is_explicit(self):
        empty = Path(self.directory.name) / "empty.sqlite"
        growth.build_database(empty)
        with sqlite3.connect(empty) as con:
            con.execute("DELETE FROM growth_activity")
            con.execute("DELETE FROM growth_users")
        result = growth.analyze({}, empty)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["kpis"], [])
        self.assertTrue(result["evidence"])  # An empty query is still traceable.

    def test_experiment_estimates_reconcile_with_groups(self):
        result = growth.analyze({"task": "experiment"}, self.db)
        self.assertEqual(result["status"], "completed")
        groups = {row["arm"]: row for row in result["evidence"][0]["rows"]}
        n0, n1 = groups["control"]["users"], groups["treatment"]["users"]
        stats = result["experiment_statistics"]
        delta = (groups["treatment"]["retained_users"] / n1 - groups["control"]["retained_users"] / n0) * 100
        self.assertAlmostEqual(stats["lift_pp"], delta)
        self.assertLess(stats["ci95_low_pp"], delta)
        self.assertGreater(stats["ci95_high_pp"], delta)
        self.assertAlmostEqual(stats["ci95_high_pp"] + stats["ci95_low_pp"], 2 * delta)
        self.assertTrue(0 <= stats["srm_p_value"] <= 1)
        self.assertTrue(math.isfinite(stats["p_value"]))

    def test_experiment_without_randomized_users_is_not_a_before_after_test(self):
        result = growth.analyze({"task": "experiment", "start": "2026-08-03", "end": "2026-08-09"}, self.db)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertNotIn("experiment_statistics", result)

    def test_small_experiment_cannot_pass_rollout_gate(self):
        result = growth.analyze({"task": "experiment", "start": "2026-08-17", "end": "2026-08-17", "filters": {"channel": "referral", "device": "web"}}, self.db)
        self.assertEqual(result["status"], "insufficient_data")
        if "decision" in result:
            self.assertFalse(result["decision"]["gates"]["sample_size"])

    def test_every_fact_has_replayable_evidence_and_json_is_finite(self):
        for task in ("diagnose", "experiment", "report"):
            with self.subTest(task=task):
                result = growth.analyze({"task": task}, self.db)
                ids = {e["id"] for e in result["evidence"]}
                for finding in result["findings"]:
                    self.assertTrue(set(finding["evidence_ids"]) <= ids)
                    if finding["kind"] == "fact":
                        self.assertTrue(finding["evidence_ids"])
                with sqlite3.connect(self.db) as con:
                    con.row_factory = sqlite3.Row
                    for evidence in result["evidence"]:
                        replayed = [dict(row) for row in con.execute(evidence["sql"], evidence["parameters"])]
                        self.assertEqual(replayed, evidence["rows"])
                json.dumps(result, allow_nan=False, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
