from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.cjpm_adapter import CjpmAdapter
from adapters.hvigor_adapter import HvigorAdapter
from driver.contracts import ProjectConfig


class _Proc:
    def __init__(self, code: int, out: str = "", err: str = "") -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = err


class DualGateAdapterTests(unittest.TestCase):
    def test_cjpm_does_not_run_test_when_build_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = ProjectConfig(
                project_name="x",
                project_type="non_ui",
                workdir=tmp,
                adapter="cjpm",
                verify_command="cjpm build",
                test_command="cjpm test",
            )

            with patch("adapters.cjpm_adapter.build_env_with_toolchain", return_value={}), patch(
                "adapters.cjpm_adapter.subprocess.run", side_effect=[_Proc(2, "build fail", "")]
            ) as run_mock:
                result = CjpmAdapter().verify(project)

            self.assertFalse(result.success)
            self.assertEqual(result.exit_code, 2)
            self.assertEqual(run_mock.call_count, 1)

    def test_cjpm_fails_when_test_fails_after_build_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = ProjectConfig(
                project_name="x",
                project_type="non_ui",
                workdir=tmp,
                adapter="cjpm",
                verify_command="cjpm build",
                test_command="cjpm test",
            )

            with patch("adapters.cjpm_adapter.build_env_with_toolchain", return_value={}), patch(
                "adapters.cjpm_adapter.subprocess.run",
                side_effect=[_Proc(0, "build ok", ""), _Proc(1, "test fail", "boom")],
            ) as run_mock:
                result = CjpmAdapter().verify(project)

            self.assertFalse(result.success)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(run_mock.call_count, 2)
            self.assertIn("[test] $ cjpm test", result.stdout)

    def test_hvigor_passes_when_build_and_test_and_artifact_all_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            artifact = workdir / "dist" / "ok.bin"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("ok", encoding="utf-8")

            project = ProjectConfig(
                project_name="x",
                project_type="ui",
                workdir=str(workdir),
                adapter="hvigor",
                verify_command="cmd /c build.cmd",
                test_command="cmd /c test.cmd",
                artifact_checks=["dist/ok.bin"],
            )

            with patch("adapters.hvigor_adapter.build_env_with_toolchain", return_value={}), patch(
                "adapters.hvigor_adapter.subprocess.run",
                side_effect=[_Proc(0, "build ok", ""), _Proc(0, "test ok", "")],
            ):
                result = HvigorAdapter().verify(project)

            self.assertTrue(result.success)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(result.artifact_checks["dist/ok.bin"])


if __name__ == "__main__":
    unittest.main()
