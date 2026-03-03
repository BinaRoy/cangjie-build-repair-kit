from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from driver.state_store import StateStore


class StateStoreTests(unittest.TestCase):
    def test_write_error_persists_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp), "run-a3")
            payload = {"category": "compile", "message": "x", "fingerprint": "abc"}

            path = store.write_error(1, payload)

            self.assertEqual(path.name, "error_iter_1.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_write_patch_plan_persists_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp), "run-a3")
            payload = {"can_apply": False, "diff_summary": "none"}

            path = store.write_patch_plan(2, payload)

            self.assertEqual(path.name, "patch_plan_iter_2.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_write_patch_diff_persists_text_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp), "run-a3")
            diff_text = "--- a/src/main.cj\n+++ b/src/main.cj\n@@\n-foo\n+bar\n"

            path = store.write_patch_diff(3, diff_text)

            self.assertEqual(path.name, "patch_iter_3.diff")
            self.assertEqual(path.read_text(encoding="utf-8"), diff_text)


if __name__ == "__main__":
    unittest.main()
