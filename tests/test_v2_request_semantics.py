"""Public request-language regressions discovered by independent V2 acceptance."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import engine
from app.domains import onboarding


class RequestSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name)/"onboarding.sqlite"
        onboarding.build_database(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_question(self, question, metric=None):
        request = {"domain": "onboarding", "question": question, "task": "diagnose", "filters": {"metric": metric} if metric else {}}
        with patch.object(engine, "database", return_value=self.path):
            return engine.analyze_domain(request)

    def test_window_return_wording_reaches_supported_analysis(self):
        result = self.run_question("比较次 1—7 日内任意回访率", "return_within_days_1_7")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["metric_contract"]["id"], "return_within_days_1_7")
        self.assertTrue(result["evidence"])

    def test_negated_metric_cannot_hide_filter_conflict(self):
        cases = [
            ("我要精确D7留存，不是7日内回访", "return_within_days_1_7"),
            ("不是精确 D7，计算次7日内回访", "new_user_retention_d7"),
            ("检查 D1，不看精确 D7", "new_user_retention_d7"),
            ("不要注册后24小时有序激活，查看精确D7", "activated_24h"),
        ]
        for question, metric in cases:
            with self.subTest(question=question):
                result = self.run_question(question, metric)
                self.assertEqual(result["status"], "needs_clarification")
                self.assertEqual(result["kpis"], [])

    def test_positive_choice_is_preserved_when_other_metric_is_negated(self):
        cases = [
            ("我要精确D7留存，不是7日内回访", "new_user_retention_d7"),
            ("不是精确 D7，计算次7日内回访", "return_within_days_1_7"),
            ("检查 D1，不看精确 D7", "new_user_retention_d1"),
        ]
        for question, metric in cases:
            with self.subTest(question=question):
                result = self.run_question(question, metric)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["metric_contract"]["id"], metric)

    def test_exclusion_alone_does_not_silently_choose_a_metric(self):
        result = self.run_question("不要精确D7留存")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["kpis"], [])

    def test_comparison_and_choice_question_are_distinguished(self):
        comparison = self.run_question("比较 D1 和 D7 留存")
        self.assertEqual(comparison["status"], "completed")
        self.assertEqual(comparison["metric_contract"]["id"], "new_user_retention_d7")
        selection = self.run_question("本次应看 D1 还是 D7？")
        self.assertEqual(selection["status"], "needs_clarification")


if __name__ == "__main__":
    unittest.main()
