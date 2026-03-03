from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from driver.contracts import ErrorSchema, KnowledgeItem, PatchAction, PatchPlan
from repair.strategies.base import RepairStrategy


@dataclass
class LLMStrategyInput:
    error: ErrorSchema
    knowledge_hits: list[KnowledgeItem]
    iteration: int
    run_id: str
    project_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMStrategyOutput:
    can_apply: bool
    rationale: str
    diff_summary: str
    actions: list[PatchAction] = field(default_factory=list)

    def to_patch_plan(self) -> PatchPlan:
        return PatchPlan(
            can_apply=self.can_apply,
            rationale=self.rationale,
            diff_summary=self.diff_summary,
            actions=self.actions,
        )


class LLMStrategy(RepairStrategy):
    def propose(self, error: ErrorSchema, context: Any) -> PatchPlan:
        data = context if isinstance(context, dict) else {}
        payload = LLMStrategyInput(
            error=error,
            knowledge_hits=list(data.get("knowledge_hits", [])),
            iteration=int(data.get("iteration", 0)),
            run_id=str(data.get("run_id", "")),
            project_name=str(data.get("project_name", "")),
            metadata=dict(data.get("metadata", {})),
        )
        return self.propose_with_schema(payload).to_patch_plan()

    def propose_with_schema(self, payload: LLMStrategyInput) -> LLMStrategyOutput:
        raise NotImplementedError
