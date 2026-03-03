from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchAction, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.patcher import apply_patch_plan
from repair.strategies.mock_llm import MockLLMStrategy


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


class MockLLMStrategyTests(unittest.TestCase):
    def test_mock_llm_strategy_adapts_output_to_patch_plan(self) -> None:
        strategy = MockLLMStrategy(
            static_actions=[
                PatchAction(
                    file_path="src/main.cj",
                    action="replace_once",
                    search="MainAbility()",
                    replace="EntryAbility()",
                )
            ]
        )
        error = ErrorSchema(
            category="link",
            file="src/main.cj",
            line=1,
            message="undefined symbol MainAbility",
            context="ctx",
            fingerprint="fp",
        )
        plan = strategy.propose(error, {"knowledge_hits": [], "iteration": 1, "run_id": "r", "project_name": "p"})
        self.assertTrue(plan.can_apply)
        self.assertEqual(plan.actions[0].replace, "EntryAbility()")

    def test_loop_with_mock_llm_strategy_does_not_bypass_applier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("MainAbility()\n", encoding="utf-8")

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
                allow_apply_patch=True,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
                require_verify_pass_after_patch=False,
            )
            strategy = MockLLMStrategy(
                static_actions=[
                    PatchAction(
                        file_path="src/main.cj",
                        action="replace_once",
                        search="MainAbility()",
                        replace="EntryAbility()",
                    )
                ]
            )

            calls = {"applier": 0}

            def applier_spy(*args, **kwargs) -> PatchResult:
                calls["applier"] += 1
                return apply_patch_plan(*args, **kwargs)

            run_loop(
                base_dir=base_dir,
                run_id="c2-mock",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="link",
                    file="src/main.cj",
                    line=1,
                    message="undefined symbol MainAbility",
                    context="ctx",
                    fingerprint="fp",
                ),
                strategy=strategy,
                applier=applier_spy,
            )

            self.assertEqual(calls["applier"], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "EntryAbility()\n")


if __name__ == "__main__":
    unittest.main()
