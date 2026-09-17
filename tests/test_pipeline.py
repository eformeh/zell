import unittest

from run import safe_filename
from scripts.report_config import format_report_date
from scripts.terminal_editor import edit_record, review_flagged_records
from scripts.validation import validate_records


class PipelineTests(unittest.TestCase):
    def test_ordinal_dates(self):
        expected = {
            "2026-10-01": "1st October 2026",
            "2026-10-02": "2nd October 2026",
            "2026-10-03": "3rd October 2026",
            "2026-10-11": "11th October 2026",
            "2026-10-12": "12th October 2026",
            "2026-10-13": "13th October 2026",
            "2026-10-21": "21st October 2026",
        }
        for value, result in expected.items():
            with self.subTest(value=value):
                self.assertEqual(format_report_date(value), result)

    def test_safe_filename_removes_windows_punctuation(self):
        record = {"id": 7, "company_name": "A/B: C & Co.'s"}
        self.assertEqual(safe_filename(record), "007_A_B_C_Co_s")

    def test_share_mismatch_is_a_warning(self):
        record = {
            "id": 1,
            "company_name": "Example Limited",
            "registration_number": "123",
            "category": "company",
            "registered_address": "Lagos",
            "incorporation_date": "JAN 1, 2026",
            "main_object": "General contract",
            "share_capital": "1,000,000",
            "directors": [{"name": "Director", "address": "Lagos"}],
            "shareholders": [{"name": "Owner", "shares": "999,999"}],
            "company_sec": None,
        }
        issues = validate_records([record])
        mismatch = [item for item in issues if item.code == "share_total_mismatch"]
        self.assertEqual(len(mismatch), 1)
        self.assertEqual(mismatch[0].severity, "warning")

    def test_terminal_editor_records_scalar_change(self):
        record = {"id": 2, "company_name": "Old Name", "category": "business"}
        answers = iter(["1", "New Name", "b"])
        changes = edit_record(record, input_fn=lambda _: next(answers), output_fn=lambda _: None)
        self.assertEqual(record["company_name"], "New Name")
        self.assertEqual(changes[0]["field"], "company_name")
        self.assertEqual(changes[0]["original"], "Old Name")

    def test_review_can_keep_warning(self):
        record = {
            "id": 3,
            "company_name": "Trust",
            "registration_number": "33",
            "category": "trustee",
            "registered_address": "Lagos",
            "incorporation_date": "JAN 1, 2026",
            "main_object": "",
            "trustees": [{"name": "Trustee", "address": "Lagos"}],
            "trustee_sec": None,
        }
        issues = validate_records([record])
        approved, changes, cancelled = review_flagged_records(
            [record], issues, input_fn=lambda _: "k", output_fn=lambda _: None
        )
        self.assertEqual(approved, [record])
        self.assertEqual(changes, [])
        self.assertFalse(cancelled)


if __name__ == "__main__":
    unittest.main()
