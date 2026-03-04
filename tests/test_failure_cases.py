from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from driver.failure_cases import FailureCaseStore, create_failure_case_record, fingerprint_bucket


class FailureCaseStructureTests(unittest.TestCase):
    def test_create_failure_case_record_contains_required_fields(self) -> None:
        record = create_failure_case_record(
            fingerprint="compile|src/main.cj|12|undefined symbol",
            context={"error": {"category": "compile", "file": "src/main.cj"}},
            plan={"can_apply": False, "actions": []},
            result={"decision": "stop_no_patch_applied"},
            run_id="run-e1",
            iteration=1,
        )

        self.assertTrue(record.case_id)
        self.assertEqual(record.fingerprint, "compile|src/main.cj|12|undefined symbol")
        self.assertIn("error", record.context)
        self.assertIn("can_apply", record.plan)
        self.assertIn("decision", record.result)

    def test_failure_case_store_writes_under_fingerprint_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FailureCaseStore(root)
            record = create_failure_case_record(
                fingerprint="compile|src/main.cj|12|undefined symbol",
                context={"error": {"category": "compile"}},
                plan={"can_apply": False},
                result={"decision": "stop"},
                run_id="run-e1",
                iteration=2,
            )

            path = store.write_case(record)

            expected_bucket = fingerprint_bucket(record.fingerprint)
            self.assertEqual(path.parent.name, expected_bucket)
            self.assertEqual(path.parent.parent.name, "failure_cases")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_id"], record.case_id)
            self.assertEqual(payload["fingerprint"], record.fingerprint)
            self.assertEqual(payload["context"]["error"]["category"], "compile")

    def test_find_similar_cases_returns_top_k_sorted_by_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FailureCaseStore(root)
            items = [
                ("compile|src/main.cj|7|undefined symbol mainability", "run-a"),
                ("compile|src/app.cj|5|undefined symbol mainability", "run-b"),
                ("runtime|src/main.cj|3|panic", "run-c"),
            ]
            for idx, (fp, run_id) in enumerate(items, start=1):
                record = create_failure_case_record(
                    fingerprint=fp,
                    context={"error": {"fingerprint": fp}},
                    plan={"can_apply": False},
                    result={"decision": "stop"},
                    run_id=run_id,
                    iteration=idx,
                )
                store.write_case(record)

            hits = store.find_similar_cases("compile|src/main.cj|7|undefined symbol mainability", top_k=2)

            self.assertEqual(len(hits), 2)
            self.assertGreaterEqual(float(hits[0]["score"]), float(hits[1]["score"]))
            self.assertEqual(hits[0]["fingerprint"], "compile|src/main.cj|7|undefined symbol mainability")


if __name__ == "__main__":
    unittest.main()
