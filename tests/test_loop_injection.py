from __future__ import annotations

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
            stderr="compile failed",
            artifact_checks={},
        )


class _StubStrategy:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        self.calls.append("strategy")
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class LoopInjectionTests(unittest.TestCase):
    def test_run_loop_supports_parser_strategy_applier_verifier_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="x",
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

            calls: list[str] = []

            def parser(_: str) -> ErrorSchema:
                calls.append("parser")
                return ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=1,
                    message="x",
                    context="x",
                    fingerprint="fp",
                )

            def applier(_: PatchPlan, __: ProjectConfig, ___: PolicyConfig) -> PatchResult:
                calls.append("applier")
                return PatchResult(applied=False, changed_files=[], changed_lines_per_file={}, message="stub")

            def verifier(
                _: PatchResult, __: ProjectConfig, ___: PolicyConfig, ____: set[str]
            ) -> tuple[bool, str]:
                calls.append("verifier")
                return True, "ok"

            strategy = _StubStrategy(calls)
            run_loop(
                base_dir=base_dir,
                run_id="inject-b4",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=parser,
                strategy=strategy,
                applier=applier,
                verifier=verifier,
            )

            self.assertEqual(calls, ["parser", "strategy", "applier", "verifier"])

    def test_syntax_error_does_not_stop_on_no_knowledge_hits_for_rule_based(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="x-syntax",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                repair_strategy="rule_based",
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=True,
                min_knowledge_hits=1,
            )

            def parser(_: str) -> ErrorSchema:
                return ErrorSchema(
                    category="syntax",
                    file="src/main.cj",
                    line=1,
                    message="syntax error",
                    context="x",
                    fingerprint="fp-syntax",
                )

            summary = run_loop(
                base_dir=base_dir,
                run_id="inject-knowledge-syntax",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=parser,
            )

            self.assertNotEqual(summary.stop_reason, "stop_no_knowledge_hits")


if __name__ == "__main__":
    unittest.main()
