from __future__ import annotations

import unittest

from driver.contracts import ErrorSchema, KnowledgeItem
from repair.planner import propose_patch_plan
from repair.strategies.rule_based import RuleBasedStrategy


class RuleBasedStrategyTests(unittest.TestCase):
    def test_rule_based_strategy_proposes_mainability_replacement(self) -> None:
        error = ErrorSchema(
            category="link",
            file="entry/src/main/cangjie/ability_mainability_entry.cj",
            line=12,
            message="undefined symbol MainAbility",
            context="...",
            fingerprint="f",
        )
        strategy = RuleBasedStrategy()
        plan = strategy.propose(error, {"knowledge_hits": []})

        self.assertTrue(plan.can_apply)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].search, "MainAbility()")
        self.assertEqual(plan.actions[0].replace, "EntryAbility()")

    def test_planner_uses_rule_based_strategy_behavior(self) -> None:
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="syntax error unexpected token",
            context="...",
            fingerprint="f2",
        )
        hits = [KnowledgeItem(source="k.md", title="k1", content="hint")]
        plan = propose_patch_plan(error, hits)

        self.assertFalse(plan.can_apply)
        self.assertIn("family=compile", plan.rationale)
        self.assertIn("k1", plan.rationale)


if __name__ == "__main__":
    unittest.main()
