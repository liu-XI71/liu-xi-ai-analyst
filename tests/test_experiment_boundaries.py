"""Integration regressions for the local-time contract and exclusive windows.

The ISO-separator regression uses the full independent-review reproduction.
Small explicit calendars cover remaining fields without consulting production
window helpers; all temporary data stays under this checkout's var directory.
"""
import contextlib
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.domains import experiments as exp


class ExperimentTimestampBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = Path(__file__).resolve().parents[1] / "var"
        directory.mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="experiment-boundaries-", dir=directory)
        cls.root = Path(cls.temporary.name)
        cls.full = cls.root / "full.sqlite"
        exp.build_database(cls.full)
        cls.small = cls.root / "calendar.sqlite"
        shutil.copyfile(cls.full, cls.small)
        with sqlite3.connect(cls.small) as con:
            for table in exp.TABLES:
                if table["name"] != "experiment_registry":
                    con.execute(f"DELETE FROM {table['name']}")
            con.execute("DELETE FROM experiment_registry WHERE experiment_id<>'underpowered'")
            con.execute("""UPDATE experiment_registry SET start_date='2024-02-22',
                end_date='2024-02-22',snapshot_date='2024-03-01',expected_assignment_count=40
                WHERE experiment_id='underpowered'""")
            registered = datetime(2024, 2, 22, 12)
            d7_start, d7_end = datetime(2024, 2, 29), datetime(2024, 3, 1)
            for arm in ("control", "treatment"):
                for index in range(20):
                    user = f"{arm}-{index}"
                    stamp = registered.isoformat(sep=" ")
                    con.execute("""INSERT INTO experiment_assignments
                        (experiment_id,user_id,arm,registered_at,assigned_at,config_version)
                        VALUES ('underpowered',?,?,?,?, 'onboarding-v1')""", (user, arm, stamp, stamp))
                    con.execute("""INSERT INTO experiment_exposures
                        (experiment_id,user_id,arm,exposed_at) VALUES ('underpowered',?,?,?)""",
                        (user, arm, (registered+timedelta(seconds=1)).isoformat(sep=" ")))
                    con.execute("INSERT INTO experiment_coverage VALUES ('underpowered',?,'2024-03-02 00:00:00',1)", (user,))
                    # Per arm exactly two D7 returns and two negative-feedback users.
                    returns = [d7_start-timedelta(seconds=1), d7_start,
                               d7_end-timedelta(seconds=1), d7_end]
                    negatives = [registered, registered+timedelta(hours=24, seconds=-1),
                                 registered+timedelta(hours=24)]
                    event = "qualified_activity" if index < 4 else "negative_feedback"
                    when = returns[index] if index < 4 else (negatives[index-4] if index < 7 else None)
                    if when is not None:
                        when = when.isoformat(sep=" ")
                        con.execute("""INSERT INTO experiment_outcomes
                            (experiment_id,user_id,event_name,event_at,ingested_at,schema_version)
                            VALUES ('underpowered',?,?,?,?,'events-v1')""", (user, event, when, when))
            con.execute("""INSERT INTO experiment_changelog
                (experiment_id,changed_at,field,old_value,new_value,material)
                VALUES ('underpowered','2024-02-22 13:00:00','note','before','after',0)""")
        with sqlite3.connect(cls.small) as con:
            con.execute("VACUUM")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @contextlib.contextmanager
    def changed(self, statements=(), full=False):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            path = Path(directory)/"changed.sqlite"
            shutil.copyfile(self.full if full else self.small, path)
            with sqlite3.connect(path) as con:
                for sql, params in statements:
                    con.execute(sql, params)
            yield path

    def review(self, path, scenario="underpowered", **request):
        return exp.analyze({"domain": "experiments", "filters": {"scenario": scenario}, **request}, path)

    def assert_blocked(self, result, gate=None):
        self.assertEqual(result["status"], "invalid_data")
        self.assertEqual(result["decision"]["code"], "invalid_data")
        self.assertFalse(result["decision"]["executes_rollout"])
        if gate is not None:
            self.assertFalse(result["decision"]["gates"][gate])
            self.assertFalse(result["experiment_statistics"]["inference_valid"])
            self.assertIsNone(result["experiment_statistics"]["primary"])
            self.assertIsNone(result["experiment_statistics"]["guardrail"])

    def test_iso_separator_cannot_turn_known_guardrail_harm_into_rollout(self):
        before = self.review(self.full, "guardrail")
        self.assertEqual(before["decision"]["code"], "stop_or_adjust")
        sql = """UPDATE experiment_outcomes SET event_at=replace(event_at,' ','T'),
            ingested_at=replace(ingested_at,' ','T')
            WHERE experiment_id='guardrail' AND event_name='negative_feedback'
              AND user_id IN (SELECT user_id FROM experiment_assignments
                WHERE experiment_id='guardrail' AND arm='treatment')"""
        with self.changed(full=True) as path:
            with sqlite3.connect(path) as con:
                changed = con.execute(sql).rowcount
                assignments = dict(con.execute("""SELECT user_id,registered_at
                    FROM experiment_assignments WHERE experiment_id='guardrail' AND arm='treatment'"""))
                events = con.execute("""SELECT user_id,event_at FROM experiment_outcomes
                    WHERE experiment_id='guardrail' AND event_name='negative_feedback'""").fetchall()
            # Independent Python instant comparison proves the business events did not change.
            actual = {user for user, stamp in events if user in assignments
                      and datetime.fromisoformat(assignments[user]) <= datetime.fromisoformat(stamp)
                      < datetime.fromisoformat(assignments[user])+timedelta(hours=24)}
            self.assertEqual(changed, 684)
            self.assertEqual(len(actual), 684)
            after = self.review(path, "guardrail")
            self.assert_blocked(after, "events")
            quality = next(item for item in after["evidence"] if item["id"] == "experiment-quality")
            self.assertEqual(quality["rows"][0]["invalid_outcomes"], changed)
            # The saved SQL remains independently executable, without a registered UDF.
            with sqlite3.connect(path) as con:
                con.row_factory = sqlite3.Row
                self.assertEqual([dict(row) for row in con.execute(quality["sql"], quality["parameters"])], quality["rows"])
                con.execute("""UPDATE experiment_outcomes SET event_at=replace(event_at,'T',' '),
                    ingested_at=replace(ingested_at,'T',' ') WHERE experiment_id='guardrail'""")
            restored = self.review(path, "guardrail")
            self.assertEqual(restored["decision"], before["decision"])
            self.assertEqual(restored["experiment_statistics"], before["experiment_statistics"])

    def test_mixed_time_representations_are_blocked_for_every_time_field(self):
        fields = [
            ("experiment_assignments", "registered_at", "eligibility"),
            ("experiment_assignments", "assigned_at", "eligibility"),
            ("experiment_exposures", "exposed_at", "events"),
            ("experiment_outcomes", "event_at", "events"),
            ("experiment_outcomes", "ingested_at", "events"),
            ("experiment_coverage", "observed_until", "collection"),
            ("experiment_changelog", "changed_at", "configuration"),
        ]
        # Each mutation affects only one row; the rest of its column stays canonical.
        variants = ["replace({field},' ','T')", "substr({field},1,10)",
                    "{field}||'.000'", "{field}||'+00:00'", "{field}||'Z'",
                    "'2024-02-30 12:00:00'", "'2024-02-22 24:00:00'", "{field}||' '"]
        for table, field, gate in fields:
            for variant in variants:
                with self.subTest(table=table, field=field, variant=variant):
                    sql = f"UPDATE {table} SET {field}={variant.format(field=field)} WHERE rowid=(SELECT MIN(rowid) FROM {table})"
                    with self.changed([(sql, ())]) as path:
                        self.assert_blocked(self.review(path), gate)

    def test_matching_assignment_strings_do_not_bypass_format_validation(self):
        sql = """UPDATE experiment_assignments SET registered_at=replace(registered_at,' ','T'),
            assigned_at=replace(assigned_at,' ','T')"""
        with self.changed([(sql, ())]) as path:
            result = self.review(path)
            self.assert_blocked(result, "eligibility")
            quality = next(item["rows"][0] for item in result["evidence"] if item["id"] == "experiment-quality")
            self.assertEqual(quality["invalid_registration_or_assignment"], 40)

    def test_registry_dates_are_canonical_and_allow_exclusive_boundaries(self):
        for field in ("start_date", "end_date", "snapshot_date"):
            for value in ("20240222", "2024-W08-4", "2024-02-30", "2024-2-22", "0000-02-22", "9999-12-31"):
                with self.subTest(field=field, value=value):
                    sql = f"UPDATE experiment_registry SET {field}=?"
                    with self.changed([(sql, (value,))]) as path:
                        # A malformed registry remains a data error with explicit request dates.
                        result = self.review(path, start="2024-02-22", end="2024-02-22")
                        self.assert_blocked(result)
                        self.assertFalse(any(item["id"] == "experiment-groups" for item in result["evidence"]))

    def test_valid_leap_day_and_exclusive_d7_and_24_hour_boundaries(self):
        result = self.review(self.small)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["experiment_statistics"]["inference_valid"])
        for gate in ("eligibility", "events", "configuration", "collection", "maturity"):
            self.assertTrue(result["decision"]["gates"][gate])
        groups = next(item["rows"] for item in result["evidence"] if item["id"] == "experiment-groups")
        for row in groups:
            self.assertEqual(row["users"], 20)
            self.assertEqual(row["retained_users"], 2)
            self.assertEqual(row["negative_users"], 2)
        self.assertEqual(result["experiment_statistics"]["primary"]["control_rate_pct"], 10)
        self.assertEqual(result["experiment_statistics"]["guardrail"]["treatment_rate_pct"], 10)

    def test_snapshot_cutoff_is_exclusive_and_watermark_is_exact(self):
        for field in ("event_at", "ingested_at"):
            with self.subTest(field=field):
                sql = f"UPDATE experiment_outcomes SET {field}='2024-03-02 00:00:00' WHERE event_id=(SELECT MIN(event_id) FROM experiment_outcomes)"
                with self.changed([(sql, ())]) as path:
                    self.assert_blocked(self.review(path), "events")
        # One second before the snapshot is valid; equal event/ingestion timestamps are allowed.
        sql = """UPDATE experiment_outcomes SET event_at='2024-03-01 23:59:59',
            ingested_at='2024-03-01 23:59:59' WHERE event_id=(SELECT MIN(event_id) FROM experiment_outcomes)"""
        with self.changed([(sql, ())]) as path:
            self.assertTrue(self.review(path)["decision"]["gates"]["events"])
        with self.changed([("UPDATE experiment_coverage SET observed_until='2024-03-01 23:59:59'", ())]) as path:
            self.assert_blocked(self.review(path), "collection")

    def test_change_at_snapshot_boundary_is_outside_observation_but_must_be_canonical(self):
        for stamp, valid in (("2024-03-02 00:00:00", True), ("2024-03-02T00:00:00", False)):
            with self.subTest(stamp=stamp), self.changed([
                ("UPDATE experiment_changelog SET changed_at=?,material=1", (stamp,))
            ]) as path:
                result = self.review(path)
                if valid:
                    self.assertTrue(result["decision"]["gates"]["configuration"])
                else:
                    self.assert_blocked(result, "configuration")


if __name__ == "__main__":
    unittest.main()
