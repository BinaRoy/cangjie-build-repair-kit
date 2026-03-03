from __future__ import annotations

import unittest

from driver.contracts import ErrorSchema, KnowledgeItem, PatchAction, PatchPlan
from repair.strategies.llm import LLMStrategy, LLMStrategyInput, LLMStrategyOutput


class _MockLLMStrategy(LLMStrategy):
    def propose_with_schema(self, payload: LLMStrategyInput) -> LLMStrategyOutput:
        return LLMStrategyOutput(
            can_apply=True,
            rationale=f"mock:{payload.error.category}",
            diff_summary="replace once",
            actions=[
                PatchAction(
                    file_path="src/main.cj",
                    action="replace_once",
                    search="MainAbility()",
                    replace="EntryAbility()",
                )
            ],
        )


class LLMStrategySchemaTests(unittest.TestCase):
    def test_schema_roundtrip_to_patch_plan(self) -> None:
        payload = LLMStrategyInput(
            error=ErrorSchema(
                category="link",
                file="src/main.cj",
                line=1,
                message="undefined symbol MainAbility",
                context="ctx",
                fingerprint="fp",
            ),
            knowledge_hits=[KnowledgeItem(source="k.md", title="k", content="hint")],
            iteration=2,
            run_id="run-c1",
            project_name="demo",
        )
        strategy = _MockLLMStrategy()
        output = strategy.propose_with_schema(payload)
        plan = output.to_patch_plan()
        self.assertIsInstance(plan, PatchPlan)
        self.assertTrue(plan.can_apply)
        self.assertEqual(plan.actions[0].replace, "EntryAbility()")

    def test_llm_strategy_implements_repair_strategy_contract(self) -> None:
        strategy = _MockLLMStrategy()
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=3,
            message="x",
            context="y",
            fingerprint="z",
        )
        plan = strategy.propose(
            error,
            {
                "knowledge_hits": [],
                "iteration": 1,
                "run_id": "run-c1",
                "project_name": "demo",
            },
        )
        self.assertIsInstance(plan, PatchPlan)
        self.assertTrue(plan.can_apply)


if __name__ == "__main__":
    unittest.main()
