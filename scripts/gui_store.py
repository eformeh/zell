import json
import secrets
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from config.settings import DRAFTS_DIR


class DraftStore:
    def __init__(self, root=DRAFTS_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, input_name, input_content, records, sources, report_settings):
        draft_id = secrets.token_urlsafe(8).replace("-", "").replace("_", "")
        folder = self.root / draft_id
        folder.mkdir(parents=True)
        input_path = folder / input_name
        input_path.write_bytes(input_content)
        state = {
            "id": draft_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "input_name": input_name,
            "input_path": str(input_path.resolve()),
            "records": records,
            "original_records": deepcopy(records),
            "sources": {str(key): value for key, value in sources.items()},
            "report_settings": report_settings,
            "edits": [],
            "skipped_ids": [],
        }
        self.save(state)
        return state

    def path(self, draft_id):
        if not draft_id or not draft_id.isalnum():
            raise FileNotFoundError("Draft not found.")
        return self.root / draft_id / "state.json"

    def load(self, draft_id):
        path = self.path(draft_id)
        if not path.is_file():
            raise FileNotFoundError("Draft not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, state):
        path = self.path(state["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(path)


def find_record(state, record_id):
    return next((record for record in state["records"] if int(record.get("id")) == int(record_id)), None)
