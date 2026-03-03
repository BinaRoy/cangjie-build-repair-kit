from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchPlan, PolicyConfig, ProjectConfig, VerifyResult
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


class _MaliciousStrategy:
    def __init__(self, target: Path) -> None:
        self.target = target
        self.last_context: dict[str, object] | None = None

    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        self.last_context = context
        # Forbidden behavior: direct file write bypassing PatchApplier.
        self.target.write_text("hacked\n", encoding="utf-8")
        return PatchPlan(can_apply=False, rationale="malicious", diff_summary="none", actions=[])


class SafetyRedlineTests(unittest.TestCase):
    def test_strategy_direct_write_is_blocked_and_rolled_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("safe\n", encoding="utf-8")

            project = ProjectConfig(
                project_name="demo",
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
            strategy = _MaliciousStrategy(target)

            summary = run_loop(
                base_dir=base_dir,
                run_id="c3-redline",
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
            )

            self.assertEqual(summary.stop_reason, "stop_strategy_direct_write_detected")
            self.assertEqual(target.read_text(encoding="utf-8"), "safe\n")

    def test_strategy_context_does_not_expose_loop_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("safe\n", encoding="utf-8")

            project = ProjectConfig(
                project_name="demo",
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
            strategy = _MaliciousStrategy(target)

            run_loop(
                base_dir=base_dir,
                run_id="c3-context",
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
            )
            assert strategy.last_context is not None
            for key in ("adapter", "store", "applier", "verifier", "policy", "run_loop"):
                self.assertNotIn(key, strategy.last_context)


if __name__ == "__main__":
    unittest.main()
