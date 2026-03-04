from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib import request

from driver.contracts import ProjectConfig
from repair.strategies.llm import LLMStrategy, LLMStrategyInput, LLMStrategyOutput
from repair.strategies.llm_output_validator import validate_llm_patch_plan_payload


Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


def _default_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read()
    if not raw:
        return {}
    out = json.loads(raw.decode("utf-8", errors="replace"))
    return out if isinstance(out, dict) else {}


@dataclass
class RealLLMStrategy(LLMStrategy):
    api_url: str
    api_key: str
    model: str
    timeout_sec: int = 30
    temperature: float = 0.0
    transport: Transport = _default_transport

    def propose_with_schema(self, payload: LLMStrategyInput) -> LLMStrategyOutput:
        if not self.api_url.strip() or not self.api_key.strip() or not self.model.strip():
            return LLMStrategyOutput(
                can_apply=False,
                rationale="Real LLM strategy is not configured.",
                diff_summary="No patch generated due to missing LLM configuration.",
                actions=[],
            )

        request_payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a repair planner. Return JSON only with fields: "
                        "can_apply(bool), rationale(str), diff_summary(str), "
                        "actions(list of {file_path, action, search, replace})."
                    ),
                },
                {"role": "user", "content": self._build_user_content(payload)},
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            response = self.transport(self.api_url, headers, request_payload, self.timeout_sec)
            return self._parse_response(response)
        except Exception as exc:
            return LLMStrategyOutput(
                can_apply=False,
                rationale=f"Real LLM request failed: {exc}",
                diff_summary="No patch generated because provider request failed.",
                actions=[],
            )

    def _build_user_content(self, payload: LLMStrategyInput) -> str:
        obj = {
            "error": {
                "category": payload.error.category,
                "file": payload.error.file,
                "line": payload.error.line,
                "message": payload.error.message,
                "context": payload.error.context,
                "fingerprint": payload.error.fingerprint,
            },
            "knowledge_hits": [
                {"source": k.source, "title": k.title, "content": k.content}
                for k in payload.knowledge_hits
            ],
            "knowledge_sources": list(payload.knowledge_sources),
            "similar_cases": list(payload.similar_cases),
            "iteration": payload.iteration,
            "run_id": payload.run_id,
            "project_name": payload.project_name,
            "metadata": payload.metadata,
        }
        return json.dumps(obj, ensure_ascii=False)

    def _parse_response(self, response: dict[str, Any]) -> LLMStrategyOutput:
        content = _extract_content_text(response)
        data = _parse_json_text(content)
        ok, reason, normalized = validate_llm_patch_plan_payload(data)
        if not ok or normalized is None:
            return LLMStrategyOutput(
                can_apply=False,
                rationale=f"Provider returned invalid structured patch plan: {reason}",
                diff_summary="No patch generated due to invalid structured patch plan.",
                actions=[],
            )
        return LLMStrategyOutput(
            can_apply=bool(normalized["can_apply"]),
            rationale=str(normalized["rationale"]),
            diff_summary=str(normalized["diff_summary"]),
            actions=list(normalized["actions"]),
        )

    @classmethod
    def from_project_config(cls, project: ProjectConfig) -> "RealLLMStrategy":
        return cls(
            api_url=project.llm_api_url,
            api_key=project.llm_api_key,
            model=project.llm_model,
            timeout_sec=project.llm_timeout_sec,
            temperature=project.llm_temperature,
        )


def _extract_content_text(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message", {})
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return ""


def _parse_json_text(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidate = raw[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None
