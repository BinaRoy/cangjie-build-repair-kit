from __future__ import annotations

import unittest

from driver.contracts import ErrorSchema, to_dict


class ErrorSchemaTests(unittest.TestCase):
    def test_error_schema_contains_required_fields(self) -> None:
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=12,
            message="undefined symbol MainAbility",
            context="at src/main.cj:12:5",
            fingerprint="compile|src/main.cj|12|undefined symbol mainability",
        )

        payload = to_dict(error)
        self.assertEqual(
            sorted(payload.keys()),
            ["category", "context", "file", "fingerprint", "line", "message"],
        )
        self.assertEqual(payload["category"], "compile")
        self.assertEqual(payload["file"], "src/main.cj")
        self.assertEqual(payload["line"], 12)


if __name__ == "__main__":
    unittest.main()
