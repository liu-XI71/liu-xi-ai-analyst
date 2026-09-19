"""Independent regression fixtures for cross-metric quality and event contracts."""
import json
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.domains import onboarding


class OnboardingBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.db = Path(cls.directory.name) / 'baseline.sqlite'
        onboarding.build_database(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def clone(self, name):
        target = Path(self.directory.name) / name
        shutil.copy2(self.db, target)
        return target

    def d7_event(self, con, device=None):
        return con.execute("""SELECT e.event_id FROM onboarding_events e JOIN onboarding_users u USING(user_id)
            WHERE u.signup_date='2026-08-30' AND e.event_name='app_active'
            AND date(e.event_time)='2026-09-06' AND (? IS NULL OR u.device=?) LIMIT 1""", (device,device)).fetchone()[0]

    def side_row(self, result, metric='new_user_retention_d7'):
        return next(row for table in result['tables'] if table['id']=='cohort-metrics'
                    for row in table['rows'] if row['metric_id']==metric)

    def availability(self, result, metric='new_user_retention_d7'):
        return next(row for row in result['data_quality']['metric_availability'] if row['metric_id']==metric)

    def test_secondary_d7_schema_is_checked_in_its_own_window(self):
        path=self.clone('secondary-schema.sqlite')
        with sqlite3.connect(path) as con:
            con.execute("UPDATE onboarding_events SET schema_version='unknown' WHERE event_id=?",(self.d7_event(con),))
        result=onboarding.analyze({'filters':{'metric':'new_user_retention_d1'}},path)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['kpis'][0]['value'],29.51)
        for metric in ('new_user_retention_d7','return_within_days_1_7'):
            self.assertFalse(self.availability(result,metric)['available'])
            self.assertFalse(self.availability(result,metric)['schema_valid'])
            self.assertIsNone(self.side_row(result,metric)['current_pct'])
            self.assertIsNone(self.side_row(result,metric)['current_successes'])
        totals=next(e['rows'] for e in result['evidence'] if e['id']=='onboarding-totals')
        self.assertTrue(all(row['d7'] is None and row['within7'] is None for row in totals))
        self.assertEqual(onboarding.analyze({'filters':{'metric':'new_user_retention_d7'}},path)['status'],'data_quality_blocked')

    def test_secondary_d7_integrity_failure_keeps_d1_usable(self):
        path=self.clone('secondary-integrity.sqlite')
        with sqlite3.connect(path) as con:
            con.execute("UPDATE onboarding_events SET device='ios' WHERE event_id=?",(self.d7_event(con,'android'),))
        result=onboarding.analyze({'filters':{'metric':'new_user_retention_d1','device':'android'}},path)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(self.availability(result,'new_user_retention_d1')['available'])
        self.assertFalse(self.availability(result)['event_integrity_valid'])
        self.assertIsNone(self.side_row(result)['current_pct'])

    def test_wrong_calendar_field_cannot_convert_earlier_activity_to_d7(self):
        path=self.clone('calendar.sqlite')
        with sqlite3.connect(path) as con:
            row=con.execute("""SELECT e.event_id,date(u.signup_date,'+7 days')
                FROM onboarding_events e JOIN onboarding_users u USING(user_id)
                WHERE u.signup_date BETWEEN '2026-08-24' AND '2026-08-30'
                  AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+2 days')
                  AND NOT EXISTS(SELECT 1 FROM onboarding_events a WHERE a.user_id=u.user_id
                    AND a.event_name='app_active' AND date(a.event_time)=date(u.signup_date,'+7 days')) LIMIT 1""").fetchone()
            con.execute('UPDATE onboarding_events SET event_date=? WHERE event_id=?',(row[1],row[0]))
        result=onboarding.analyze({},path)
        self.assertEqual(result['status'],'data_quality_blocked')
        self.assertFalse(result['kpis'])
        check=next(x for x in result['data_quality']['checks'] if x['id']=='event_integrity')
        self.assertGreater(check['observed'],0)

    def test_corrupted_date_outside_window_still_found_via_time_or_batch(self):
        path=self.clone('outside-date.sqlite')
        with sqlite3.connect(path) as con:
            event=con.execute("SELECT event_id FROM onboarding_events WHERE event_date='2026-08-25' AND event_name='app_active' LIMIT 1").fetchone()[0]
            con.execute("UPDATE onboarding_events SET event_date='2030-01-01' WHERE event_id=?",(event,))
        self.assertEqual(onboarding.analyze({'filters':{'metric':'new_user_retention_d1'}},path)['status'],'data_quality_blocked')

    def test_device_relabel_cannot_escape_its_user_partition_checks(self):
        path=self.clone('device-schema.sqlite')
        with sqlite3.connect(path) as con:
            con.execute("UPDATE onboarding_events SET device='ios',schema_version='unknown' WHERE event_id=?",(self.d7_event(con,'android'),))
        result=onboarding.analyze({'filters':{'device':'android'}},path)
        self.assertEqual(result['status'],'data_quality_blocked')
        checks={row['id']:row for row in result['data_quality']['checks']}
        self.assertEqual(checks['schema_version']['observed'],1)
        self.assertGreater(checks['event_integrity']['observed'],0)

    def test_wrong_batch_membership_blocked_even_when_counts_reconcile(self):
        path=self.clone('batch-consistent-count.sqlite')
        with sqlite3.connect(path) as con:
            event=self.d7_event(con,'android')
            con.execute("UPDATE onboarding_events SET batch_id=event_date || ':ios' WHERE event_id=?",(event,))
            con.execute('UPDATE onboarding_ingest_batches SET expected_events=(SELECT COUNT(*) FROM onboarding_events e WHERE e.batch_id=onboarding_ingest_batches.batch_id)')
        result=onboarding.analyze({'filters':{'device':'android'}},path)
        self.assertEqual(result['status'],'data_quality_blocked')
        self.assertEqual(next(x for x in result['data_quality']['checks'] if x['id']=='continuous_watermark')['status'],'passed')
        self.assertGreater(next(x for x in result['data_quality']['checks'] if x['id']=='event_integrity')['observed'],0)

    def test_malformed_event_time_is_a_quality_failure(self):
        path=self.clone('bad-timestamp.sqlite')
        with sqlite3.connect(path) as con:
            con.execute("UPDATE onboarding_events SET event_time='not-a-timestamp' WHERE event_id=?",(self.d7_event(con),))
        self.assertEqual(onboarding.analyze({},path)['status'],'data_quality_blocked')

    def request_fixture(self,name,first_kind='first_feed_success',later_kind='first_feed_failure',missing_id=False,conflict=False):
        path=self.clone(name)
        with sqlite3.connect(path) as con:
            con.execute('DELETE FROM onboarding_events');con.execute('DELETE FROM onboarding_users')
            for day in ('2026-08-17','2026-08-24'):
                uid=day;signup=datetime.fromisoformat(day+' 12:00:00')
                con.execute('INSERT INTO onboarding_users VALUES(?,?,?,?,?,?)',(uid,onboarding._stamp(signup),day,'organic','web','1.8.0'))
                first_id=None if missing_id else 'request-1'
                values=[('signup',0,None,None),('onboarding_completed',60,None,None),
                        ('feed_requested',120,first_id,None),(first_kind,130,first_id,None),
                        ('content_consumed',190,None,60),('feed_requested',240,'request-2',None),
                        (later_kind,250,'request-2',None),('app_active',7*86400,None,None)]
                if conflict:values.append(('first_feed_failure',140,first_id,None))
                for i,(event_name,offset,request_id,duration) in enumerate(values):
                    at=signup+timedelta(seconds=offset)
                    con.execute('INSERT INTO onboarding_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (day+':'+str(i),uid,event_name,onboarding._stamp(at),onboarding._stamp(at+timedelta(seconds=1)),at.date().isoformat(),'organic','web','1.8.0',at.date().isoformat()+':web','1.0',request_id,duration))
            con.execute('UPDATE onboarding_ingest_batches SET expected_events=(SELECT COUNT(*) FROM onboarding_events e WHERE e.batch_id=onboarding_ingest_batches.batch_id)')
        return path

    def fixture_result(self,path):
        return onboarding.analyze({'start':'2026-08-24','end':'2026-08-24','compare_start':'2026-08-17','compare_end':'2026-08-17'},path)

    def test_first_success_later_failure_is_zero_first_request_failures(self):
        result=self.fixture_result(self.request_fixture('first-success.sqlite'))
        self.assertEqual(result['status'],'completed')
        rows=next(x['rows'] for x in result['tables'] if x['id']=='version-slices')
        self.assertTrue(all(row['feed_failed']==0 and row['first_feed_failure_pct']==0 for row in rows))
        self.assertTrue(all(row['feed_requested']==1 for row in rows))

    def test_first_failure_later_success_stays_a_first_request_failure(self):
        result=self.fixture_result(self.request_fixture('first-failure.sqlite','first_feed_failure','first_feed_success'))
        self.assertEqual(result['status'],'completed')
        rows=next(x['rows'] for x in result['tables'] if x['id']=='version-slices')
        self.assertTrue(all(row['feed_failed']==1 and row['first_feed_failure_pct']==100 for row in rows))

    def test_unknown_or_conflicting_first_result_is_not_zero_failure(self):
        for mode in ('missing_id','conflict'):
            result=self.fixture_result(self.request_fixture(mode+'.sqlite',missing_id=mode=='missing_id',conflict=mode=='conflict'))
            self.assertEqual(result['status'],'completed')  # Valid D7 still answers the main question.
            rows=next(x['rows'] for x in result['tables'] if x['id']=='version-slices')
            self.assertTrue(all(row['first_feed_failure_pct'] is None for row in rows))
            self.assertTrue(all(row['feed_result_unresolved']==1 for row in rows))
            self.assertTrue(any('request_id' in text for text in result['limitations']))

    def test_extreme_dates_return_structured_failures(self):
        for request in ({'start':'0001-01-01','end':'0001-01-01'},
                        {'start':'0001-01-02','end':'0001-01-10'},
                        {'start':'9999-12-31','end':'9999-12-31'}):
            result=onboarding.analyze(request,self.db)
            self.assertIn(result['status'],('needs_clarification','insufficient_data'))
            self.assertFalse(result['kpis'])
            json.dumps(result,allow_nan=False)

    def test_default_business_results_match_frozen_snapshot(self):
        frozen=json.loads((Path(__file__).parents[1]/'web/demo/onboarding.json').read_text())
        result=onboarding.analyze({},self.db)
        self.assertEqual(result['kpis'],frozen['kpis'])
        self.assertEqual(result['funnel'],frozen['funnel'])
        for name in ('cohort-metrics','onboarding-decomposition','version-slices'):
            actual=next(t['rows'] for t in result['tables'] if t['id']==name)
            expected=next(t['rows'] for t in frozen['tables'] if t['id']==name)
            self.assertEqual(len(actual),len(expected))
            for row,gold in zip(actual,expected):
                self.assertEqual({key:row[key] for key in gold},gold)

    def test_all_new_quality_sql_evidence_can_be_replayed(self):
        path=self.clone('evidence-schema.sqlite')
        with sqlite3.connect(path) as con:
            con.execute("UPDATE onboarding_events SET schema_version='unknown' WHERE event_id=?",(self.d7_event(con),))
        result=onboarding.analyze({'filters':{'metric':'new_user_retention_d1'}},path)
        with sqlite3.connect(path) as con:
            con.row_factory=sqlite3.Row
            for evidence in result['evidence']:
                self.assertEqual([dict(row) for row in con.execute(evidence['sql'],evidence['parameters'])],evidence['rows'])
        ids={e['id'] for e in result['evidence']}
        for metric in result['data_quality']['metric_availability']:
            self.assertTrue(set(metric['evidence_ids'])<=ids)
        json.dumps(result,allow_nan=False)


if __name__=='__main__':unittest.main()
