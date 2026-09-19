"""Business invariants: exact windows, ITT, source reconciliation and decisions."""
import contextlib
import json
import math
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.domains import experiments as exp


class ExperimentReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.db = Path(cls.directory.name) / "experiments.sqlite"
        exp.build_database(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @contextlib.contextmanager
    def changed_database(self, statements):
        with tempfile.TemporaryDirectory(dir=self.directory.name) as temporary:
            database = Path(temporary) / "changed.sqlite"
            shutil.copyfile(self.db, database)
            with sqlite3.connect(database) as con:
                for statement in statements:
                    if isinstance(statement, tuple):
                        con.execute(*statement)
                    else:
                        con.execute(statement)
            yield database

    def analyze(self, scenario="healthy_gain", **extra):
        return exp.analyze({"filters": {"scenario": scenario}, **extra}, self.db)

    def test_all_scenarios_review_from_data(self):
        expected = {
            "healthy_gain": ("completed", "review_for_gradual_rollout"),
            "srm": ("invalid_data", "invalid_data"),
            "guardrail": ("completed", "stop_or_adjust"),
            "immature": ("waiting_for_maturity", "waiting_for_maturity"),
            "underpowered": ("completed", "insufficient_evidence"),
            "unequal_allocation": ("completed", "review_for_gradual_rollout"),
            "config_change": ("invalid_data", "invalid_data"),
            "data_gap": ("invalid_data", "invalid_data"),
        }
        for scenario, outcome in expected.items():
            with self.subTest(scenario=scenario):
                result = self.analyze(scenario)
                self.assertEqual((result["status"], result["decision"]["code"]), outcome)
                self.assertFalse(result["decision"]["executes_rollout"])
                json.dumps(result, allow_nan=False)

    def test_metrics_reconcile_with_independent_event_walk(self):
        result = self.analyze()
        with sqlite3.connect(self.db) as con:
            assignments = con.execute("SELECT user_id,arm,registered_at FROM experiment_assignments WHERE experiment_id='healthy_gain'").fetchall()
            events = con.execute("SELECT user_id,event_name,event_at FROM experiment_outcomes WHERE experiment_id='healthy_gain'").fetchall()
        users = {user: (arm, datetime.fromisoformat(stamp)) for user, arm, stamp in assignments}
        retained, negative, any_return = set(), set(), set()
        for user, event, stamp in events:
            arm, registered = users[user]
            when = datetime.fromisoformat(stamp)
            day = (when.date()-registered.date()).days
            if event == "qualified_activity":
                if day == 7:
                    retained.add(user)
                if 1 <= day <= 7:
                    any_return.add(user)
            if event == "negative_feedback" and registered <= when < registered+timedelta(hours=24):
                negative.add(user)
        groups = {row["arm"]: row for row in next(e for e in result["evidence"] if e["id"] == "experiment-groups")["rows"]}
        for arm in ("control", "treatment"):
            group = {user for user, (actual, _) in users.items() if actual == arm}
            self.assertEqual(groups[arm]["users"], len(group))
            self.assertEqual(groups[arm]["retained_users"], len(group & retained))
            self.assertEqual(groups[arm]["negative_users"], len(group & negative))
            self.assertLess(groups[arm]["exposed_users"], groups[arm]["users"])
        self.assertGreater(len(any_return), len(retained))
        primary = result["experiment_statistics"]["primary"]
        expected_lift = (groups["treatment"]["retained_users"]/groups["treatment"]["users"] - groups["control"]["retained_users"]/groups["control"]["users"])*100
        self.assertAlmostEqual(primary["lift_pp"], expected_lift)

    def test_no_exposure_does_not_remove_users_from_itt(self):
        expected = self.analyze()["experiment_statistics"]["primary"]
        with self.changed_database(["DELETE FROM experiment_exposures WHERE experiment_id='healthy_gain'"]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["experiment_statistics"]["primary"], expected)
        self.assertEqual(result["decision"]["code"], "review_for_gradual_rollout")

    def test_duplicate_events_do_not_inflate_unique_users(self):
        expected = self.analyze()["experiment_statistics"]
        statement = """INSERT INTO experiment_outcomes(experiment_id,user_id,event_name,event_at,ingested_at,schema_version)
          SELECT experiment_id,user_id,event_name,event_at,ingested_at,schema_version
          FROM experiment_outcomes WHERE experiment_id='healthy_gain'"""
        with self.changed_database([statement]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["experiment_statistics"], expected)

    def test_exact_d7_excludes_d1_and_end_boundary(self):
        with self.changed_database([
            "DELETE FROM experiment_outcomes WHERE experiment_id='healthy_gain' AND event_name='qualified_activity'",
            """INSERT INTO experiment_outcomes(experiment_id,user_id,event_name,event_at,ingested_at,schema_version)
            SELECT experiment_id,user_id,'qualified_activity',datetime(date(registered_at),'+1 day'),datetime(date(registered_at),'+1 day','+1 minute'),'events-v1'
            FROM experiment_assignments WHERE experiment_id='healthy_gain'""",
        ]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["experiment_statistics"]["primary"]["control_rate_pct"], 0)
        self.assertIsNone(result["experiment_statistics"]["primary"]["relative_lift_pct"])
        # A user whose D8 boundary remains before the snapshot can have a D8 event; it is not D7.
        with self.changed_database([
            "DELETE FROM experiment_outcomes WHERE experiment_id='healthy_gain' AND event_name='qualified_activity'",
            """INSERT INTO experiment_outcomes(experiment_id,user_id,event_name,event_at,ingested_at,schema_version)
            SELECT experiment_id,user_id,'qualified_activity',datetime(date(registered_at),'+8 days'),datetime(date(registered_at),'+8 days','+1 minute'),'events-v1'
            FROM experiment_assignments WHERE experiment_id='healthy_gain' AND date(registered_at)<='2026-08-29'""",
        ]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["experiment_statistics"]["primary"]["treatment_rate_pct"], 0)

    def test_negative_feedback_24_hour_boundary_is_exclusive(self):
        with self.changed_database([
            "DELETE FROM experiment_outcomes WHERE experiment_id='healthy_gain' AND event_name='negative_feedback'",
            """INSERT INTO experiment_outcomes(experiment_id,user_id,event_name,event_at,ingested_at,schema_version)
            SELECT experiment_id,user_id,'negative_feedback',datetime(registered_at,'+24 hours'),datetime(registered_at,'+24 hours','+1 minute'),'events-v1'
            FROM experiment_assignments WHERE experiment_id='healthy_gain'""",
        ]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["experiment_statistics"]["guardrail"]["control_rate_pct"], 0)
        self.assertEqual(result["experiment_statistics"]["guardrail"]["treatment_rate_pct"], 0)

    def test_immature_cohort_is_not_zero_or_silently_dropped(self):
        result = self.analyze("immature")
        groups = next(e for e in result["evidence"] if e["id"] == "experiment-groups")["rows"]
        self.assertTrue(all(row["users"] > 0 and row["mature_users"] == 0 for row in groups))
        self.assertTrue(all(row["retained_users"] is None for row in groups))
        self.assertIsNone(result["experiment_statistics"]["primary"])
        self.assertFalse(result["experiment_statistics"]["inference_valid"])
        self.assertFalse(any(chart["id"] == "experiment-outcomes" for chart in result["charts"]))

    def test_unequal_allocation_uses_registered_ratio_and_rates(self):
        result = self.analyze("unequal_allocation")
        rows = next(e for e in result["evidence"] if e["id"] == "experiment-groups")["rows"]
        groups = {row["arm"]: row for row in rows}
        actual = result["experiment_statistics"]["srm"]
        self.assertGreater(actual["p_value"], .001)
        self.assertLess(exp.srm_test(groups["control"]["users"], groups["treatment"]["users"], .5)["p_value"], .001)
        self.assertGreater(result["plan"]["treatment_required"], result["plan"]["control_required"])
        difference = (groups["treatment"]["retained_users"]/groups["treatment"]["users"] - groups["control"]["retained_users"]/groups["control"]["users"])*100
        self.assertAlmostEqual(result["experiment_statistics"]["primary"]["lift_pp"], difference)

    def test_srm_and_quality_failures_suppress_effect_estimates(self):
        for scenario in ("srm", "config_change", "data_gap"):
            with self.subTest(scenario=scenario):
                result = self.analyze(scenario)
                self.assertFalse(result["experiment_statistics"]["inference_valid"])
                self.assertIsNone(result["experiment_statistics"]["primary"])
                self.assertIsNone(result["experiment_statistics"]["guardrail"])

    def test_scenario_label_does_not_determine_decision(self):
        # Repair the SRM registration to match actual assignment policy: the same name now passes.
        with self.changed_database(["UPDATE experiment_registry SET expected_treatment_share=.7 WHERE experiment_id='srm'"]) as database:
            result = exp.analyze({"filters": {"scenario": "srm"}}, database)
        self.assertEqual(result["status"], "completed")
        self.assertNotEqual(result["decision"]["code"], "invalid_data")
        # Damage the healthy scenario: user identity duplication must block it.
        statement = """INSERT INTO experiment_assignments(experiment_id,user_id,arm,registered_at,assigned_at,config_version)
          SELECT experiment_id,user_id,arm,registered_at,assigned_at,config_version
          FROM experiment_assignments WHERE experiment_id='healthy_gain' LIMIT 1"""
        with self.changed_database([statement]) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["decision"]["code"], "invalid_data")
        self.assertFalse(result["decision"]["gates"]["identity"])

    def test_data_integrity_boundaries(self):
        cases = {
            "source_reconciliation": "DELETE FROM experiment_assignments WHERE assignment_id=(SELECT MIN(assignment_id) FROM experiment_assignments WHERE experiment_id='healthy_gain')",
            "identity": "UPDATE experiment_assignments SET arm='unexpected' WHERE assignment_id=(SELECT MIN(assignment_id) FROM experiment_assignments WHERE experiment_id='healthy_gain')",
            "eligibility": "UPDATE experiment_assignments SET registered_at='2025-01-01 00:00:00' WHERE assignment_id=(SELECT MIN(assignment_id) FROM experiment_assignments WHERE experiment_id='healthy_gain')",
            "collection": "UPDATE experiment_coverage SET complete=0 WHERE experiment_id='healthy_gain' AND user_id=(SELECT MIN(user_id) FROM experiment_coverage WHERE experiment_id='healthy_gain')",
            "events": "UPDATE experiment_outcomes SET schema_version='unknown' WHERE event_id=(SELECT MIN(event_id) FROM experiment_outcomes WHERE experiment_id='healthy_gain')",
            "configuration": "INSERT INTO experiment_changelog(experiment_id,changed_at,field,old_value,new_value,material) VALUES ('healthy_gain','2026-09-02 00:00:00','policy','old','new',1)",
        }
        for check, statement in cases.items():
            with self.subTest(check=check), self.changed_database([statement]) as database:
                result = exp.analyze({}, database)
                self.assertEqual(result["decision"]["code"], "invalid_data")
                self.assertFalse(result["decision"]["gates"][check])
                self.assertIsNone(result["experiment_statistics"]["primary"])

    def test_cross_arm_exposure_is_invalid(self):
        with self.changed_database(["UPDATE experiment_exposures SET arm=CASE arm WHEN 'control' THEN 'treatment' ELSE 'control' END WHERE exposure_id=(SELECT MIN(exposure_id) FROM experiment_exposures WHERE experiment_id='healthy_gain')"]) as database:
            result = exp.analyze({}, database)
        self.assertFalse(result["decision"]["gates"]["events"])
        self.assertEqual(result["decision"]["code"], "invalid_data")

    def test_guardrail_harm_blocks_despite_positive_primary(self):
        result = self.analyze("guardrail")
        self.assertGreater(result["experiment_statistics"]["primary"]["ci_low_pp"], 1)
        self.assertTrue(result["experiment_statistics"]["guardrail"]["harm_exceeds_margin"])
        self.assertEqual(result["decision"]["code"], "stop_or_adjust")

    def test_nonsignificant_harm_does_not_imply_noninferiority(self):
        with self.changed_database(["UPDATE experiment_registry SET negative_margin=.008 WHERE experiment_id='healthy_gain'"]) as database:
            result = exp.analyze({}, database)
        negative = result["experiment_statistics"]["guardrail"]
        self.assertGreater(negative["p_value"], .05)
        self.assertFalse(negative["noninferior"])
        self.assertFalse(result["decision"]["gates"]["negative_feedback"])
        self.assertEqual(result["decision"]["code"], "insufficient_evidence")

    def test_main_metric_harm_cannot_pass(self):
        statement = """DELETE FROM experiment_outcomes WHERE experiment_id='healthy_gain'
        AND event_name='qualified_activity' AND user_id IN
        (SELECT user_id FROM experiment_assignments WHERE experiment_id='healthy_gain' AND arm='treatment')"""
        with self.changed_database([statement]) as database:
            result = exp.analyze({}, database)
        self.assertLess(result["experiment_statistics"]["primary"]["ci_high_pp"], 0)
        self.assertEqual(result["decision"]["code"], "stop_or_adjust")

    def test_no_users_is_insufficient_evidence(self):
        statements = [f"DELETE FROM {table['name']} WHERE experiment_id='healthy_gain'" for table in exp.TABLES if table["name"] != "experiment_registry"]
        statements.append("UPDATE experiment_registry SET expected_assignment_count=0 WHERE experiment_id='healthy_gain'")
        with self.changed_database(statements) as database:
            result = exp.analyze({}, database)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["decision"]["code"], "insufficient_evidence")
        self.assertIsNone(result["experiment_statistics"]["srm"]["p_value"])

    def test_invalid_parameters_and_posthoc_filters_are_not_ignored(self):
        cases = [[], {"domain": "growth"}, {"task": "diagnose"}, {"filters": []}, {"filters": ""},
                 {"filters": {"scenario": ["healthy_gain"]}}, {"filters": {"scenario": "missing"}},
                 {"filters": {"scenario": "' OR 1=1--"}}, {"filters": {"channel": "organic"}},
                 {"start": "2026-08-17"}, {"start": "invalid", "end": "invalid"},
                 {"start": "2026-08-17", "end": "2026-08-25"},
                 {"compare_start": "2026-08-01", "compare_end": "2026-08-07"}]
        for request in cases:
            with self.subTest(request=request):
                result = exp.analyze(request, self.db)
                self.assertEqual(result["status"], "needs_clarification")
                self.assertEqual(result["kpis"], [])

    def test_corrupt_registry_never_causes_division_by_zero(self):
        for field, value in (("expected_treatment_share", 0), ("alpha", 0), ("power", 1), ("mde", 0), ("negative_margin", 0)):
            with self.subTest(field=field), self.changed_database([(f"UPDATE experiment_registry SET {field}=? WHERE experiment_id='healthy_gain'", (value,))]) as database:
                result = exp.analyze({}, database)
                self.assertEqual(result["status"], "invalid_data")
                json.dumps(result, allow_nan=False)

    def test_every_result_is_evidenced_and_replayable(self):
        for scenario in (entry["value"] for entry in exp.SCENARIOS):
            with self.subTest(scenario=scenario):
                result = self.analyze(scenario, task="report")
                ids = {item["id"] for item in result["evidence"]}
                for item in result["findings"] + result["kpis"] + result["checks"] + result["charts"]:
                    self.assertTrue(item["evidence_ids"])
                    self.assertLessEqual(set(item["evidence_ids"]), ids)
                with sqlite3.connect(self.db) as con:
                    con.row_factory = sqlite3.Row
                    for evidence in result["evidence"]:
                        rows = [dict(row) for row in con.execute(evidence["sql"], evidence["parameters"])]
                        self.assertEqual(rows, evidence["rows"])

    def test_build_is_reproducible_idempotent_and_preserves_other_domains(self):
        with tempfile.TemporaryDirectory(dir=self.directory.name) as temporary:
            database = Path(temporary)/"other.sqlite"
            exp.build_database(database)
            with sqlite3.connect(database) as con:
                con.execute("CREATE TABLE other_business (value TEXT)")
                con.execute("INSERT INTO other_business VALUES ('preserved')")
                before = con.execute("SELECT COUNT(*),SUM(event_id) FROM experiment_outcomes").fetchone()
            exp.build_database(database)
            with sqlite3.connect(self.db) as original, sqlite3.connect(database) as repeated:
                self.assertEqual(repeated.execute("SELECT value FROM other_business").fetchone()[0], "preserved")
                self.assertEqual(repeated.execute("SELECT COUNT(*),SUM(event_id) FROM experiment_outcomes").fetchone(), before)
                for table in ("experiment_registry", "experiment_assignments", "experiment_outcomes"):
                    self.assertEqual(original.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall(), repeated.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall())


class StatisticalProperties(unittest.TestCase):
    def test_score_intervals_are_finite_at_extreme_outcomes(self):
        low, high = exp.wilson_interval(0, 100)
        self.assertAlmostEqual(low, 0)
        self.assertAlmostEqual(high, .03699349820698568)
        for counts in ((0, 100, 0, 100), (0, 100, 100, 100), (100, 100, 100, 100), (1, 4, 2, 5)):
            result = exp.rate_difference(*counts)
            self.assertLessEqual(result["ci_low_pp"], result["lift_pp"])
            self.assertGreaterEqual(result["ci_high_pp"], result["lift_pp"])
            self.assertTrue(0 <= result["p_value"] <= 1)
            json.dumps(result, allow_nan=False)

    def test_difference_interval_reverses_with_arm_order(self):
        first = exp.rate_difference(281, 1000, 465, 1400)
        reverse = exp.rate_difference(465, 1400, 281, 1000)
        self.assertAlmostEqual(first["lift_pp"], -reverse["lift_pp"])
        self.assertAlmostEqual(first["ci_low_pp"], -reverse["ci_high_pp"])
        self.assertAlmostEqual(first["p_value"], reverse["p_value"])

    def test_power_design_increases_for_smaller_mde_or_higher_power(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary)/"small.sqlite"
            exp.build_database(database)
            with sqlite3.connect(database) as con:
                con.row_factory = sqlite3.Row
                registry = dict(con.execute("SELECT * FROM experiment_registry WHERE experiment_id='healthy_gain'").fetchone())
        baseline = exp.sample_size_plan(registry)
        self.assertGreater(baseline["control_required"], 200)
        small = exp.sample_size_plan({**registry, "mde": .015})
        high = exp.sample_size_plan({**registry, "power": .9})
        self.assertGreater(small["control_required"], baseline["control_required"])
        self.assertGreater(high["control_required"], baseline["control_required"])
        unequal = exp.sample_size_plan({**registry, "expected_treatment_share": .7})
        self.assertGreater(unequal["total_required"], baseline["total_required"])
        self.assertGreater(unequal["treatment_required"], unequal["control_required"])

    def test_srm_expected_counts_and_invalid_inputs(self):
        self.assertAlmostEqual(exp.srm_test(300, 700, .7)["p_value"], 1)
        self.assertLess(exp.srm_test(300, 700, .5)["p_value"], 1e-10)
        self.assertFalse(exp.srm_test(1, 1, .5)["approximation_valid"])
        with self.assertRaises(ValueError):
            exp.srm_test(30, 70, 1)
        with self.assertRaises(ValueError):
            exp.rate_difference(4, 3, 2, 4)


if __name__ == "__main__":
    unittest.main()
