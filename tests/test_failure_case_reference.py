from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchPlan, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.failure_cases import FailureCaseStore, create_failure_case_record
from driver.loop import run_loop


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="compile failed",
            artifact_checks={},
        )


class _NoopStrategy:
    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        del error, context
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class FailureCaseReferenceTests(unittest.TestCase):
    def test_patch_plan_records_referenced_case_ids_and_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)

            store = FailureCaseStore(base_dir)
            case = create_failure_case_record(
                fingerprint="compile|src/main.cj|7|compile failed",
                context={"error": {"message": "compile failed"}},
                plan={"can_apply": False},
                result={"decision": "stop"},
                run_id="seed",
                iteration=1,
            )
            store.write_case(case)

            project = ProjectConfig(
                project_name="e4",
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
            )

            run_loop(
                base_dir=base_dir,
                run_id="e4-run",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=7,
                    message="compile failed",
                    context="ctx",
                    fingerprint="compile|src/main.cj|7|compile failed",
                ),
                strategy=_NoopStrategy(),
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            plan_payload = json.loads(
                (base_dir / "runs" / "e4-run" / "patch_plan_iter_1.json").read_text(encoding="utf-8")
            )
            self.assertIn("referenced_case_ids", plan_payload)
            self.assertIn("case_match_reason", plan_payload)
            self.assertIn(case.case_id, plan_payload["referenced_case_ids"])
            self.assertTrue(str(plan_payload["case_match_reason"]).strip())


if __name__ == "__main__":
    unittest.main()
