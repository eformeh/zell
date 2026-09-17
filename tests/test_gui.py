import io
import json
import tempfile
import time
import unittest
from pathlib import Path

import app as gui_app
from scripts.gui_store import DraftStore


class GuiWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        gui_app.store = DraftStore(root / "drafts")
        gui_app.RUNS_DIR = root / "runs"
        gui_app.jobs.clear()
        gui_app.app.config.update(TESTING=True)
        self.client = gui_app.app.test_client()
        self.record = {
            "id": 1,
            "company_name": "GUI SAMPLE BUSINESS",
            "registration_number": "1234567",
            "category": "business",
            "registered_address": "1 TEST ROAD, LAGOS",
            "incorporation_date": "JAN 1, 2026",
            "main_object": "GENERAL CONTRACT",
            "proprietors": [{"name": "SAMPLE OWNER", "address": "1 TEST ROAD, LAGOS"}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def create_draft(self):
        response = self.client.post(
            "/drafts",
            data={
                "source_file": (io.BytesIO(json.dumps([self.record]).encode("utf-8")), "sample.json"),
                "report_date": "2026-10-03",
                "recipient_title": "The Branch Manager",
                "recipient_organization": "Test Bank Plc",
                "recipient_address": "1 Bank Road\nLagos State",
                "salutation": "Dear Sir/Ma,",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        return response.headers["Location"].rstrip("/").split("/")[-1]

    def test_home_upload_edit_preview_and_generate(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        draft_id = self.create_draft()

        review = self.client.get(f"/drafts/{draft_id}")
        self.assertEqual(review.status_code, 200)
        self.assertIn(b"GUI SAMPLE BUSINESS", review.data)
        self.assertIn(b"Test Bank Plc", gui_app.store.load(draft_id)["report_settings"]["recipient"]["organization"].encode())

        update = self.client.post(
            f"/drafts/{draft_id}/records/1",
            data={
                "company_name": "UPDATED GUI BUSINESS",
                "registration_number": "1234567",
                "registered_address": "2 UPDATED ROAD, LAGOS",
                "incorporation_date": "JAN 1, 2026",
                "main_object": "UPDATED CONTRACT",
                "proprietors_name": ["SAMPLE OWNER"],
                "proprietors_address": ["2 UPDATED ROAD, LAGOS"],
                "save_action": "review",
            },
        )
        self.assertEqual(update.status_code, 302)
        state = gui_app.store.load(draft_id)
        self.assertEqual(state["records"][0]["company_name"], "UPDATED GUI BUSINESS")
        self.assertEqual(len(state["edits"]), 1)

        preview = self.client.get(f"/drafts/{draft_id}/preview/1")
        self.assertEqual(preview.status_code, 200)
        self.assertIn(b"3rd October 2026", preview.data)
        self.assertIn(b"UPDATED GUI BUSINESS", preview.data)

        generation = self.client.post(f"/drafts/{draft_id}/generate", data={"no_pdf": "on"})
        self.assertEqual(generation.status_code, 302)
        job_id = generation.headers["Location"].rstrip("/").split("/")[-1]
        for _ in range(100):
            status = self.client.get(f"/api/jobs/{job_id}").get_json()
            if status["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["summary"]["html_generated"], 1)
        self.assertEqual(status["summary"]["pdf_generated"], 0)
        detail = self.client.get(f"/runs/{status['run']}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"UPDATED_GUI_BUSINESS", detail.data)


if __name__ == "__main__":
    unittest.main()
