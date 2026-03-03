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


class _ContractStrategy:
    def __init__(self) -> None:
        self.context_seen: dict[str, object] | None = None

    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        self.context_seen = context
        required = {"knowledge_hits", "iteration", "run_id", "project_name"}
        if not required.issubset(context.keys()):
            missing = ",".join(sorted(required.difference(context.keys())))
            raise AssertionError(f"missing_context_keys:{missing}")
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class LoopContractTests(unittest.TestCase):
    def test_strategy_context_contract_contains_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="demo-project",
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

            strategy = _ContractStrategy()

            run_loop(
                base_dir=base_dir,
                run_id="contract-b5",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=1,
                    message="err",
                    context="ctx",
                    fingerprint="fp",
                ),
                strategy=strategy,
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False,
                    changed_files=[],
                    changed_lines_per_file={},
                    message="stub",
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            self.assertIsNotNone(strategy.context_seen)
            self.assertEqual(strategy.context_seen["run_id"], "contract-b5")


if __name__ == "__main__":
    unittest.main()
