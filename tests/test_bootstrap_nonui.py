from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.main import _bootstrap_non_ui


class BootstrapNonUITests(unittest.TestCase):
    def test_bootstrap_nonui_generates_configs_and_follow_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = root / "proj"
            (project_root / "src").mkdir(parents=True)
            (project_root / "cjpm.toml").write_text('name = "demo"\n', encoding="utf-8")
            out = root / "out"

            rc = _bootstrap_non_ui(
                project_root=project_root.as_posix(),
                output_dir=out.as_posix(),
                project_name="demo",
                force=True,
            )

            self.assertEqual(rc, 0)
            project_cfg = out / "project.demo.toml"
            policy_cfg = out / "policy.default.toml"
            guide = out / "FOLLOW_GUIDE.md"
            self.assertTrue(project_cfg.exists())
            self.assertTrue(policy_cfg.exists())
            self.assertTrue(guide.exists())
            text = project_cfg.read_text(encoding="utf-8")
            self.assertIn('workdir = "', text)
            self.assertIn('editable_paths = ["src", "cjpm.toml"]', text)
            guide_text = guide.read_text(encoding="utf-8")
            self.assertIn("validate", guide_text)
            self.assertIn("run repair loop", guide_text.lower())

    def test_bootstrap_nonui_marks_verify_command_when_cjpm_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = root / "proj"
            project_root.mkdir(parents=True)
            out = root / "out"

            rc = _bootstrap_non_ui(
                project_root=project_root.as_posix(),
                output_dir=out.as_posix(),
                project_name="demo2",
                force=True,
            )

            self.assertEqual(rc, 0)
            text = (out / "project.demo2.toml").read_text(encoding="utf-8")
            self.assertIn('verify_command = "<fill_verify_command>"', text)


if __name__ == "__main__":
    unittest.main()
