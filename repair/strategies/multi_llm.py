from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from driver.contracts import ErrorSchema
from repair.strategies.real_llm import RealLLMStrategy, Transport, _default_transport


@dataclass
class MultiModelLLMStrategy:
    api_url: str
    api_key: str
    model_primary: str
    model_secondary: str
    route_rule: str = "error_type_or_complexity"
    secondary_categories: list[str] = field(default_factory=lambda: ["syntax", "generic", "type"])
    complexity_threshold: int = 220
    timeout_sec: int = 30
    temperature: float = 0.0
    transport: Transport = _default_transport

    def __post_init__(self) -> None:
        self._last_route_decision: dict[str, Any] = {}
        self._primary = RealLLMStrategy(
            api_url=self.api_url,
            api_key=self.api_key,
            model=self.model_primary,
            timeout_sec=self.timeout_sec,
            temperature=self.temperature,
            transport=self.transport,
        )
        self._secondary = RealLLMStrategy(
            api_url=self.api_url,
            api_key=self.api_key,
            model=self.model_secondary,
            timeout_sec=self.timeout_sec,
            temperature=self.temperature,
            transport=self.transport,
        )
        self.route_rule = (self.route_rule or "error_type_or_complexity").strip().lower()
        self.secondary_categories = [x.strip().lower() for x in self.secondary_categories if x.strip()]
        if self.complexity_threshold <= 0:
            self.complexity_threshold = 220

    def propose(self, error: ErrorSchema, context: Any):
        data = context if isinstance(context, dict) else {}
        selected_key, reason, score = self._route(error, data)
        strategy = self._secondary if selected_key == "secondary" else self._primary
        plan = strategy.propose(error, data)
        self._last_route_decision = {
            "route_rule": self.route_rule,
            "selected_model_key": selected_key,
            "selected_model": self.model_secondary if selected_key == "secondary" else self.model_primary,
            "reason": reason,
            "complexity_score": score,
            "category": error.category,
        }
        return plan

    def get_last_route_decision(self) -> dict[str, Any]:
        return dict(self._last_route_decision)

    def _route(self, error: ErrorSchema, data: dict[str, Any]) -> tuple[str, str, int]:
        category = (error.category or "").strip().lower()
        score = _complexity_score(error, data)
        use_secondary = False
        reason = "default_primary"
        if self.route_rule in {"error_type", "error_type_or_complexity"} and category in self.secondary_categories:
            use_secondary = True
            reason = "error_type"
        if self.route_rule in {"complexity", "error_type_or_complexity"} and score >= self.complexity_threshold:
            use_secondary = True
            reason = "complexity" if reason == "default_primary" else "error_type+complexity"
        return ("secondary" if use_secondary else "primary", reason, score)


def _complexity_score(error: ErrorSchema, context: dict[str, Any]) -> int:
    text_score = len(error.message or "") + len(error.context or "")
    knowledge_hits = context.get("knowledge_hits", [])
    knowledge_score = 20 * (len(knowledge_hits) if isinstance(knowledge_hits, list) else 0)
    return text_score + knowledge_score
