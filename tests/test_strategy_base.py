from __future__ import annotations

import unittest

from driver.contracts import ErrorSchema, PatchPlan
from repair.strategies.base import RepairStrategy


class _DemoStrategy(RepairStrategy):
    def propose(self, error: ErrorSchema, context: dict[str, str]) -> PatchPlan:
        return PatchPlan(
            can_apply=False,
            rationale=f"demo:{error.category}",
            diff_summary="none",
            actions=[],
        )


class StrategyBaseTests(unittest.TestCase):
    def test_repair_strategy_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            RepairStrategy()

    def test_subclass_can_implement_propose_contract(self) -> None:
        strategy = _DemoStrategy()
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="x",
            context="x",
            fingerprint="f",
        )
        plan = strategy.propose(error, {"k": "v"})
        self.assertIsInstance(plan, PatchPlan)
        self.assertFalse(plan.can_apply)


if __name__ == "__main__":
    unittest.main()
