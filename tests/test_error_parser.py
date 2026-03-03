from __future__ import annotations

import unittest

from driver.contracts import ErrorSchema
from repair.error_parser import extract_root_cause


class ErrorParserTests(unittest.TestCase):
    def test_extract_root_cause_returns_error_schema(self) -> None:
        log = "\n".join(
            [
                "Compiling project...",
                "src/main.cj:12:5 error: Undefined symbol MainAbility",
                "build failed",
            ]
        )

        error = extract_root_cause(log)
        self.assertIsInstance(error, ErrorSchema)
        self.assertEqual(error.category, "link")
        self.assertEqual(error.file, "src/main.cj")
        self.assertEqual(error.line, 12)
        self.assertIn("undefined symbol", error.message.lower())
        self.assertTrue(error.fingerprint)

    def test_fingerprint_is_stable_for_equivalent_logs(self) -> None:
        log1 = "\n".join(
            [
                "src/main.cj:12:5 error: Undefined symbol MainAbility",
                "at parser stage",
            ]
        )
        log2 = "\n".join(
            [
                "[stderr] SRC/MAIN.CJ:12:9 ERROR:   undefined symbol   MainAbility  ",
                "more traces...",
            ]
        )

        error1 = extract_root_cause(log1)
        error2 = extract_root_cause(log2)
        self.assertEqual(error1.fingerprint, error2.fingerprint)


if __name__ == "__main__":
    unittest.main()
