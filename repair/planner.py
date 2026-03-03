from __future__ import annotations

from driver.contracts import ErrorSchema, KnowledgeItem, PatchPlan
from repair.strategies.rule_based import RuleBasedStrategy


def propose_patch_plan(error: ErrorSchema, knowledge_hits: list[KnowledgeItem]) -> PatchPlan:
    return RuleBasedStrategy().propose(error, {"knowledge_hits": knowledge_hits})
