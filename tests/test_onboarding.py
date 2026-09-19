"""Independent event-level checks for calendar retention, maturity and quality gates."""
import json
import shutil
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from app.domains import onboarding


class OnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / "onboarding.sqlite"
        onboarding.build_database(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def cloned(self, name):
        path = Path(self.temp.name) / name
        shutil.copy2(self.db, path)
        return path

    def test_dataset_covers_110_days_and_idempotence_preserves_other_domains(self):
        other = self.cloned("idempotence.sqlite")
        with sqlite3.connect(other) as con:
            before = con.execute("SELECT COUNT(*),MIN(event_time),MAX(event_time) FROM onboarding_events").fetchone()
            self.assertEqual(con.execute("SELECT COUNT(DISTINCT signup_date) FROM onboarding_users").fetchone()[0], 110)
            con.execute("CREATE TABLE separate_business (value TEXT)")
            con.execute("INSERT INTO separate_business VALUES ('preserve')")
        onboarding.build_database(other)
        with sqlite3.connect(other) as con:
            self.assertEqual(before, con.execute("SELECT COUNT(*),MIN(event_time),MAX(event_time) FROM onboarding_events").fetchone())
            self.assertEqual(con.execute("SELECT value FROM separate_business").fetchone()[0], "preserve")
        regenerated = Path(self.temp.name) / "regenerated.sqlite"
        onboarding.build_database(regenerated)
        with sqlite3.connect(self.db) as original, sqlite3.connect(regenerated) as repeated:
            self.assertEqual(original.execute("SELECT * FROM onboarding_events ORDER BY event_id").fetchall(), repeated.execute("SELECT * FROM onboarding_events ORDER BY event_id").fetchall())

    def test_exact_d1_d7_and_window_match_independent_sets(self):
        result = onboarding.analyze({}, self.db)
        with sqlite3.connect(self.db) as con:
            users = dict(con.execute("SELECT user_id,signup_date FROM onboarding_users WHERE signup_date BETWEEN '2026-08-24' AND '2026-08-30'"))
            events = con.execute("SELECT user_id,event_date FROM onboarding_events WHERE event_name='app_active' AND ingested_at<='2026-09-19 08:00:00'").fetchall()
        sets = {"new_user_retention_d1": set(), "new_user_retention_d7": set(), "return_within_days_1_7": set()}
        for uid, when in events:
            if uid not in users:
                continue
            offset = (date.fromisoformat(when)-date.fromisoformat(users[uid])).days
            if offset == 1:
                sets["new_user_retention_d1"].add(uid)
            if offset == 7:
                sets["new_user_retention_d7"].add(uid)
            if 1 <= offset <= 7:
                sets["return_within_days_1_7"].add(uid)
        table = next(table for table in result["tables"] if table["id"] == "cohort-metrics")
        for row in table["rows"]:
            if row["metric_id"] in sets:
                self.assertEqual(row["current_users"], len(users))
                self.assertEqual(row["current_successes"], len(sets[row["metric_id"]]))
        self.assertGreater(len(sets["return_within_days_1_7"]), len(sets["new_user_retention_d7"]))
        self.assertGreater(len(sets["new_user_retention_d7"]-sets["new_user_retention_d1"]), 0)

    def test_natural_language_metric_inference_and_explicit_conflict(self):
        for question, metric in [("分析精确 D1 留存", "new_user_retention_d1"), ("看次 1—7 日内回访", "return_within_days_1_7"), ("对比 24 小时有序激活率", "activated_24h")]:
            result = onboarding.analyze({"question": question}, self.db)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["metric_contract"]["id"], metric)
        result = onboarding.analyze({"question": "请分析精确 D1", "filters": {"metric": "new_user_retention_d7"}}, self.db)
        self.assertEqual(result["status"], "needs_clarification")
        self.assertFalse(result["kpis"])
        ambiguous = onboarding.analyze({"question": "本次应看 D1 还是 D7？"}, self.db)
        self.assertEqual(ambiguous["status"], "needs_clarification")

    def test_late_data_is_actual_unavailable_events_not_changed_wording(self):
        request = {"filters": {"scenario": "late_data"}}
        late = onboarding.analyze(request, self.db)
        recovered = onboarding.analyze({"filters": {"scenario": "recovered"}}, self.db)
        full = onboarding.analyze({}, self.db)
        self.assertEqual(late["status"], "data_quality_blocked")
        self.assertEqual(late["kpis"], [])
        self.assertEqual(late["charts"], [])
        self.assertEqual(late["data_quality"]["watermark"], "2026-09-04 00:00:00")
        self.assertEqual(len(late["data_quality"]["affected_batches"]), 3)
        self.assertTrue(all(row["expected_events"] > row["observed_events"] for row in late["data_quality"]["affected_batches"]))
        self.assertEqual(recovered["status"], "completed")
        self.assertEqual(full["kpis"], recovered["kpis"])
        with sqlite3.connect(self.db) as con:
            late_count = con.execute("SELECT COUNT(*) FROM onboarding_events WHERE event_date BETWEEN '2026-09-04' AND '2026-09-06' AND device='android' AND ingested_at<=?", (onboarding.SCENARIOS['late_data']['as_of'],)).fetchone()[0]
            recovered_count = con.execute("SELECT COUNT(*) FROM onboarding_events WHERE event_date BETWEEN '2026-09-04' AND '2026-09-06' AND device='android' AND ingested_at<=?", (onboarding.SCENARIOS['recovered']['as_of'],)).fetchone()[0]
        self.assertEqual(late_count, 0)
        self.assertGreater(recovered_count, 0)

    def test_late_android_partition_does_not_block_ios_cohort(self):
        result = onboarding.analyze({"filters": {"scenario": "late_data", "device": "ios"}}, self.db)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["data_quality"]["watermark"], "2026-09-07 00:00:00")

    def test_completed_d1_can_be_used_while_d7_stays_null(self):
        result = onboarding.analyze({"filters": {"scenario": "late_data", "metric": "new_user_retention_d1"}}, self.db)
        self.assertEqual(result["status"], "completed")
        rows = next(table["rows"] for table in result["tables"] if table["id"] == "cohort-metrics")
        d7 = next(row for row in rows if row["metric_id"] == "new_user_retention_d7")
        self.assertIsNone(d7["current_pct"])
        self.assertIsNone(d7["current_successes"])
        evidence = next(item for item in result["evidence"] if item["id"] == "onboarding-totals")
        self.assertTrue(all(row["d7"] is None for row in evidence["rows"]))

    def test_observation_maturity_is_distinct_from_arrival_quality(self):
        cases = [
            {"start": "2026-09-12", "end": "2026-09-12"},
            {"start": "2026-09-18", "end": "2026-09-18", "filters": {"metric": "activated_24h"}},
            {"start": "2026-09-07", "end": "2026-09-07", "filters": {"metric": "activated_24h", "scenario": "recovered"}},
        ]
        for request in cases:
            with self.subTest(request=request):
                result = onboarding.analyze(request, self.db)
                self.assertEqual(result["status"], "insufficient_data")
                self.assertEqual(result["kpis"], [])
                self.assertEqual(result["decision"]["status"], "wait_for_maturity")
        mature = onboarding.analyze({"start": "2026-09-11", "end": "2026-09-11"}, self.db)
        self.assertEqual(mature["status"], "completed")

    def test_unknown_schema_blocks_before_business_interpretation(self):
        damaged = self.cloned("schema.sqlite")
        with sqlite3.connect(damaged) as con:
            con.execute("UPDATE onboarding_events SET schema_version='unknown' WHERE event_id=(SELECT event_id FROM onboarding_events WHERE event_date='2026-08-25' LIMIT 1)")
        result = onboarding.analyze({}, damaged)
        self.assertEqual(result["status"], "data_quality_blocked")
        self.assertEqual(result["kpis"], [])
        check = next(row for row in result["data_quality"]["checks"] if row["id"] == "schema_version")
        self.assertEqual(check["observed"], 1)

    def test_missing_manifest_and_deleted_events_cannot_pass_quality(self):
        for mode in ("manifest", "event"):
            damaged = self.cloned(f"missing-{mode}.sqlite")
            with sqlite3.connect(damaged) as con:
                if mode == "manifest":
                    con.execute("DELETE FROM onboarding_ingest_batches WHERE event_date='2026-08-25' AND device='android'")
                else:
                    con.execute("DELETE FROM onboarding_events WHERE event_id=(SELECT event_id FROM onboarding_events WHERE event_date='2026-08-25' AND device='android' LIMIT 1)")
            self.assertEqual(onboarding.analyze({}, damaged)["status"], "data_quality_blocked")

    def test_sql_parameterization_and_restricted_filters(self):
        result = onboarding.analyze({"filters": {"channel": ["paid_search"], "device": "android"}}, self.db)
        self.assertEqual(result["status"], "completed")
        evidence = next(item for item in result["evidence"] if item["id"] == "onboarding-strata")
        self.assertIn(":filter_channel_0", evidence["sql"])
        self.assertNotIn("paid_search", evidence["sql"])
        self.assertTrue(all(row["channel"] == "paid_search" and row["device"] == "android" for row in evidence["rows"]))
        for request in [
            {"filters": {"channel": "' OR 1=1 --"}}, {"filters": {"user_id": "u000001"}},
            {"filters": {"device": []}}, {"filters": {"app_version": "2.0"}},
            {"filters": {"metric": "arbitrary_sql"}}, {"filters": {"scenario": "future"}},
            {"filters": []}, {"question": []}, {"task": "delete"},
            {"start": "2026-02-30", "end": "2026-08-30"}, {"start": "2026-08-30"},
            {"start": "2026-08-30", "end": "2026-08-24"},
            {"compare_start": "2026-08-29", "compare_end": "2026-08-30"},
        ]:
            with self.subTest(request=request):
                self.assertEqual(onboarding.analyze(request, self.db)["status"], "needs_clarification")

    def test_unavailable_ranges_and_empty_version_are_not_zero(self):
        for request in [
            {"start": "2026-05-30", "end": "2026-06-03"},
            {"start": "2026-09-18", "end": "2026-09-20"},
            {"filters": {"app_version": "1.9.0", "device": "ios"}},
        ]:
            result = onboarding.analyze(request, self.db)
            self.assertEqual(result["status"], "insufficient_data")
            self.assertFalse(result["kpis"])

    def test_decomposition_closes_and_reverses_with_actual_data(self):
        direct = onboarding.analyze({}, self.db)
        reverse = onboarding.analyze({"start": "2026-08-17", "end": "2026-08-23", "compare_start": "2026-08-24", "compare_end": "2026-08-30"}, self.db)
        for result in (direct, reverse):
            kpis = {item["id"]: item for item in result["kpis"]}
            self.assertAlmostEqual(kpis["mix_pp"]["value"] + kpis["performance_pp"]["value"], kpis["new_user_retention_d7"]["delta"], places=2)
        self.assertEqual(direct["kpis"][0]["delta"], -reverse["kpis"][0]["delta"])
        self.assertEqual(direct["kpis"][2]["value"], -reverse["kpis"][2]["value"])

    def test_all_fact_evidence_is_replayable_and_json_finite(self):
        for request in ({}, {"task": "report"}, {"task": "funnel"}, {"task": "quality"}, {"filters": {"scenario": "late_data"}}, {"filters": {"scenario": "recovered"}}):
            result = onboarding.analyze(request, self.db)
            evidence_ids = {item["id"] for item in result["evidence"]}
            for finding in result["findings"]:
                self.assertTrue(finding["evidence_ids"])
                self.assertTrue(set(finding["evidence_ids"]) <= evidence_ids)
            with sqlite3.connect(self.db) as con:
                con.row_factory = sqlite3.Row
                for item in result["evidence"]:
                    self.assertEqual([dict(row) for row in con.execute(item["sql"], item["parameters"])], item["rows"])
            json.dumps(result, allow_nan=False, ensure_ascii=False)

    def test_public_schema_contains_no_diagnosis_truth(self):
        forbidden = ("groundtruth", "ground_truth", "root_cause", "expected_answer", "failure_label")
        with sqlite3.connect(self.db) as con:
            schema = " ".join(row[0] for row in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")).lower()
        self.assertFalse(any(word in schema for word in forbidden))
        meta = onboarding.metadata()
        self.assertEqual(len(meta["metrics"]), 10)
        self.assertEqual(meta["default_request"]["domain"], "onboarding")

    def test_ordered_funnel_and_exclusive_24h_boundary_on_independent_fixture(self):
        path = self.cloned("tiny-fixture.sqlite")
        with sqlite3.connect(path) as con:
            con.execute("DELETE FROM onboarding_events")
            con.execute("DELETE FROM onboarding_users")
            events = []
            for cohort_day in ("2026-08-17", "2026-08-24"):
                signup = datetime.fromisoformat(cohort_day + " 23:59:50")
                for index in range(4):
                    uid = cohort_day + ":" + str(index)
                    con.execute("INSERT INTO onboarding_users VALUES (?,?,?,?,?,?)", (uid, onboarding._stamp(signup), cohort_day, "organic", "web", "1.8.0"))
                    timings = [("signup", 0, None)]
                    if index == 0:  # Correct path.
                        timings += [("onboarding_completed", 60, None), ("first_feed_success", 120, None), ("content_consumed", 180, 60)]
                    elif index == 1:  # Feed before onboarding: not an ordered conversion.
                        timings += [("first_feed_success", 60, None), ("onboarding_completed", 120, None), ("content_consumed", 180, 60)]
                    elif index == 2:  # Exact 24h endpoint is outside the half-open window.
                        timings += [("onboarding_completed", 60, None), ("first_feed_success", 120, None), ("content_consumed", 86400, 60)]
                    else:
                        timings += [("onboarding_completed", 86400, None), ("first_feed_success", 86460, None)]
                    if index < 3:
                        # A D1 event can be only 20 seconds after a late-night signup.
                        offset = (20, 7*86400, 2*86400)[index]
                        timings.append(("app_active", offset, None))
                    for name, offset, duration in timings:
                        at = signup + timedelta(seconds=offset)
                        events.append((f"fixture-{len(events)}", uid, name, onboarding._stamp(at), onboarding._stamp(at+timedelta(seconds=1)), at.date().isoformat(), "organic", "web", "1.8.0", at.date().isoformat()+":web", "1.0", None, duration))
            con.executemany("INSERT INTO onboarding_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", events)
            con.execute("UPDATE onboarding_ingest_batches SET expected_events=(SELECT COUNT(*) FROM onboarding_events e WHERE e.batch_id=onboarding_ingest_batches.batch_id)")
        result = onboarding.analyze({"start": "2026-08-24", "end": "2026-08-24", "compare_start": "2026-08-17", "compare_end": "2026-08-17"}, path)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([row["current_users"] for row in result["funnel"]["steps"]], [4,3,2,1])
        values = {row["metric_id"]: row for table in result["tables"] if table["id"] == "cohort-metrics" for row in table["rows"]}
        self.assertEqual(values["new_user_retention_d1"]["current_successes"], 1)
        self.assertEqual(values["new_user_retention_d7"]["current_successes"], 1)
        self.assertEqual(values["return_within_days_1_7"]["current_successes"], 3)
        self.assertEqual(values["activated_24h"]["current_successes"], 1)

    def test_daily_active_is_not_new_registration_count(self):
        result = onboarding.analyze({}, self.db)
        evidence = next(item for item in result["evidence"] if item["id"] == "onboarding-daily-active")
        with sqlite3.connect(self.db) as con:
            events = con.execute("SELECT user_id,event_date,event_name,ingested_at FROM onboarding_events WHERE event_date='2026-08-24'").fetchall()
        independent = {uid for uid, day, name, arrival in events if name in ("app_active", "content_consumed") and arrival <= onboarding.SCENARIOS['business_drop']['as_of']}
        self.assertEqual(next(row["active_users"] for row in evidence["rows"] if row["event_date"] == '2026-08-24'), len(independent))


if __name__ == '__main__':
    unittest.main()
