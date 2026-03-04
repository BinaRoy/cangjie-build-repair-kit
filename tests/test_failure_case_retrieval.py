from __future__ import annotations

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


class _CaptureStrategy:
    def __init__(self) -> None:
        self.context_seen: dict[str, object] | None = None

    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        del error
        self.context_seen = context
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class FailureCaseRetrievalTests(unittest.TestCase):
    def test_run_loop_injects_similar_cases_into_strategy_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="e3",
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

            store = FailureCaseStore(base_dir)
            record = create_failure_case_record(
                fingerprint="compile|src/main.cj|7|compile failed",
                context={"error": {"message": "compile failed"}},
                plan={"can_apply": False},
                result={"decision": "stop"},
                run_id="seed-run",
                iteration=1,
            )
            store.write_case(record)

            strategy = _CaptureStrategy()
            run_loop(
                base_dir=base_dir,
                run_id="e3-run",
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
                strategy=strategy,
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            self.assertIsNotNone(strategy.context_seen)
            similar = strategy.context_seen.get("similar_cases")
            self.assertIsInstance(similar, list)
            self.assertTrue(similar)
            self.assertEqual(similar[0]["case_id"], record.case_id)


if __name__ == "__main__":
    unittest.main()
