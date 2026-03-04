from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchPlan, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="src/main.cj:7:2 error: compile failed",
            artifact_checks={},
        )


class _NoopStrategy:
    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        del error, context
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class E5CaseReuseRegressionTests(unittest.TestCase):
    def test_second_occurrence_reuses_historical_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="e5",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
                similar_case_top_k=3,
            )
            parser = lambda _text: ErrorSchema(  # noqa: E731
                category="compile",
                file="src/main.cj",
                line=7,
                message="compile failed",
                context="ctx",
                fingerprint="compile|src/main.cj|7|compile failed",
            )

            run_loop(
                base_dir=base_dir,
                run_id="e5-run-1",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=parser,
                strategy=_NoopStrategy(),
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            run_loop(
                base_dir=base_dir,
                run_id="e5-run-2",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=parser,
                strategy=_NoopStrategy(),
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            case_files = list((base_dir / "failure_cases").rglob("*.json"))
            self.assertEqual(len(case_files), 1)
            case_payload = json.loads(case_files[0].read_text(encoding="utf-8"))

            plan_payload = json.loads(
                (base_dir / "runs" / "e5-run-2" / "patch_plan_iter_1.json").read_text(encoding="utf-8")
            )
            self.assertIn(case_payload["case_id"], plan_payload["referenced_case_ids"])
            self.assertIn("Top similar cases", plan_payload["case_match_reason"])


if __name__ == "__main__":
    unittest.main()
