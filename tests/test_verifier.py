from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.verifier import evaluate_verify_result


class VerifierTests(unittest.TestCase):
    def test_stops_after_build_failure(self) -> None:
        result = evaluate_verify_result(
            workdir=Path("."),
            build_returncode=2,
            build_stdout="build out",
            build_stderr="build err",
            build_command="build",
            test_returncode=None,
            test_stdout="",
            test_stderr="",
            test_command="test",
            artifact_checks=[],
        )
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.command, "build")
        self.assertEqual(result.artifact_checks, {})

    def test_evaluates_test_and_artifact_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            artifact = workdir / "dist" / "ok.bin"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("ok", encoding="utf-8")

            result = evaluate_verify_result(
                workdir=workdir,
                build_returncode=0,
                build_stdout="build out",
                build_stderr="",
                build_command="build",
                test_returncode=0,
                test_stdout="test out",
                test_stderr="",
                test_command="test",
                artifact_checks=["dist/ok.bin"],
            )
            self.assertTrue(result.success)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.command, "build && test")
            self.assertTrue(result.artifact_checks["dist/ok.bin"])
            self.assertIn("[test] $ test", result.stdout)


if __name__ == "__main__":
    unittest.main()
