from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import PatchAction, PatchPlan, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.error_parser import extract_root_cause
from repair.patcher import apply_patch_plan


class _UnknownFailAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="compilation halted at stage 2",
            artifact_checks={},
        )


def _project(tmp: str) -> ProjectConfig:
    return ProjectConfig(
        project_name="x",
        project_type="non_ui",
        workdir=tmp,
        adapter="cjpm",
        verify_command="cjpm build",
        editable_paths=["src"],
    )


class MilestoneA6RegressionTests(unittest.TestCase):
    def test_fingerprint_stable_for_equivalent_error_lines(self) -> None:
        e1 = extract_root_cause("src/main.cj:12:5 error: Undefined symbol MainAbility")
        e2 = extract_root_cause("[stderr] SRC/MAIN.CJ:12:9 ERROR: undefined symbol MainAbility")
        self.assertEqual(e1.fingerprint, e2.fingerprint)

    def test_rollback_restores_file_when_multi_action_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "src").mkdir(parents=True)
            a = workdir / "src" / "a.cj"
            b = workdir / "src" / "b.cj"
            a.write_text("v=old\n", encoding="utf-8")
            b.write_text("v=old\n", encoding="utf-8")

            plan = PatchPlan(
                can_apply=True,
                rationale="r",
                diff_summary="d",
                actions=[
                    PatchAction(file_path="src/a.cj", action="replace_once", search="old", replace="new"),
                    PatchAction(file_path="src/b.cj", action="replace_once", search="missing", replace="new"),
                ],
            )
            result = apply_patch_plan(plan, _project(tmp), PolicyConfig(allow_apply_patch=True))
            self.assertFalse(result.applied)
            self.assertEqual(a.read_text(encoding="utf-8"), "v=old\n")

    def test_loop_writes_structured_patch_plan_even_on_early_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workdir = base / "work"
            (workdir / "src").mkdir(parents=True)
            project = _project(str(workdir))
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_root_cause_extracted=True,
                require_knowledge_lookup_on_failure=False,
            )

            run_loop(base, "a6-reg", project, policy, _UnknownFailAdapter())

            run_dir = base / "runs" / "a6-reg"
            self.assertTrue((run_dir / "error_iter_1.json").exists())
            patch_plan = json.loads((run_dir / "patch_plan_iter_1.json").read_text(encoding="utf-8"))
            self.assertIn("can_apply", patch_plan)
            self.assertIn("diff_summary", patch_plan)


if __name__ == "__main__":
    unittest.main()
