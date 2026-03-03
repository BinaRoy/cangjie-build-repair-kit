from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.contracts import PatchAction, PatchPlan, PolicyConfig, ProjectConfig
from repair.patcher import apply_patch_plan


def _project(tmp: str) -> ProjectConfig:
    return ProjectConfig(
        project_name="x",
        project_type="non_ui",
        workdir=tmp,
        adapter="cjpm",
        verify_command="cjpm build",
        editable_paths=["src"],
    )


class PatcherTests(unittest.TestCase):
    def test_dry_run_does_not_modify_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("let a = 1\n", encoding="utf-8")

            plan = PatchPlan(
                can_apply=True,
                rationale="test",
                diff_summary="replace literal",
                actions=[
                    PatchAction(
                        file_path="src/main.cj",
                        action="replace_once",
                        search="1",
                        replace="2",
                    )
                ],
            )

            result = apply_patch_plan(plan, _project(tmp), PolicyConfig(allow_apply_patch=True), dry_run=True)
            self.assertTrue(result.applied)
            self.assertEqual(target.read_text(encoding="utf-8"), "let a = 1\n")

    def test_rollback_restores_previous_file_when_later_action_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            file_a = workdir / "src" / "a.cj"
            file_b = workdir / "src" / "b.cj"
            file_a.parent.mkdir(parents=True)
            file_a.write_text("value = old\n", encoding="utf-8")
            file_b.write_text("value = old\n", encoding="utf-8")

            plan = PatchPlan(
                can_apply=True,
                rationale="test",
                diff_summary="two actions, second fails",
                actions=[
                    PatchAction(
                        file_path="src/a.cj",
                        action="replace_once",
                        search="old",
                        replace="new",
                    ),
                    PatchAction(
                        file_path="src/b.cj",
                        action="replace_once",
                        search="missing",
                        replace="new",
                    ),
                ],
            )

            result = apply_patch_plan(plan, _project(tmp), PolicyConfig(allow_apply_patch=True))
            self.assertFalse(result.applied)
            self.assertIn("rolled back", result.message.lower())
            self.assertEqual(file_a.read_text(encoding="utf-8"), "value = old\n")
            self.assertEqual(file_b.read_text(encoding="utf-8"), "value = old\n")


if __name__ == "__main__":
    unittest.main()
