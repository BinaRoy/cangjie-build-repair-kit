from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from driver.contracts import ProjectConfig
from driver.contracts import ErrorSchema, KnowledgeItem
from knowledge.mcp_provider import MCPKnowledgeProvider, MCPSettings
from knowledge.retriever import retrieve_local_knowledge


class KnowledgeProvider(Protocol):
    name: str

    def retrieve(self, base_dir: Path, error: ErrorSchema) -> list[KnowledgeItem]:
        raise NotImplementedError


class LocalKnowledgeProvider:
    name = "local"

    def __init__(self) -> None:
        self._last_decision: dict[str, object] = {}

    def retrieve(self, base_dir: Path, error: ErrorSchema) -> list[KnowledgeItem]:
        hits = retrieve_local_knowledge(base_dir, error)
        self._last_decision = {
            "selected_provider": "local",
            "fallback_used": False,
            "reason": "local_provider",
            "hit_count": len(hits),
        }
        return hits

    def get_last_decision(self) -> dict[str, object]:
        return dict(self._last_decision)


class HybridKnowledgeProvider:
    name = "hybrid"

    def __init__(self, mcp_provider: KnowledgeProvider, local_provider: KnowledgeProvider) -> None:
        self._mcp_provider = mcp_provider
        self._local_provider = local_provider
        self._last_decision: dict[str, object] = {}

    def retrieve(self, base_dir: Path, error: ErrorSchema) -> list[KnowledgeItem]:
        try:
            mcp_hits = self._mcp_provider.retrieve(base_dir, error)
            if mcp_hits:
                self._last_decision = {
                    "selected_provider": "mcp",
                    "fallback_used": False,
                    "reason": "mcp_hit",
                    "hit_count": len(mcp_hits),
                }
                return mcp_hits
        except Exception as exc:
            self._last_decision = {
                "selected_provider": "local",
                "fallback_used": True,
                "reason": "mcp_exception",
                "error": str(exc),
            }
            return self._local_provider.retrieve(base_dir, error)
        local_hits = self._local_provider.retrieve(base_dir, error)
        self._last_decision = {
            "selected_provider": "local",
            "fallback_used": True,
            "reason": "mcp_no_hits",
            "hit_count": len(local_hits),
        }
        return local_hits

    def get_last_decision(self) -> dict[str, object]:
        return dict(self._last_decision)


@dataclass
class KnowledgeProviderSelection:
    mode: str
    provider: KnowledgeProvider


def resolve_knowledge_provider(mode: str) -> KnowledgeProviderSelection:
    return resolve_knowledge_provider_for_project(mode, None)


def resolve_knowledge_provider_for_project(mode: str, project: ProjectConfig | None) -> KnowledgeProviderSelection:
    normalized = (mode or "local").strip().lower()
    if normalized not in {"local", "mcp", "hybrid"}:
        raise ValueError(f"Unsupported knowledge_provider: {mode}")
    if normalized == "mcp":
        settings = MCPSettings(
            command=(project.mcp_server_command if project else ""),
            args=list(project.mcp_server_args) if project else [],
            server_url=(project.mcp_server_url if project else ""),
            headers=list(project.mcp_headers) if project else [],
            tool_name=(project.mcp_tool_name if project else "query-docs"),
            timeout_sec=(project.mcp_timeout_sec if project else 15),
            max_items=(project.mcp_max_items if project else 5),
        )
        return KnowledgeProviderSelection(mode=normalized, provider=MCPKnowledgeProvider(settings))
    if normalized == "hybrid":
        settings = MCPSettings(
            command=(project.mcp_server_command if project else ""),
            args=list(project.mcp_server_args) if project else [],
            server_url=(project.mcp_server_url if project else ""),
            headers=list(project.mcp_headers) if project else [],
            tool_name=(project.mcp_tool_name if project else "query-docs"),
            timeout_sec=(project.mcp_timeout_sec if project else 15),
            max_items=(project.mcp_max_items if project else 5),
        )
        return KnowledgeProviderSelection(
            mode=normalized,
            provider=HybridKnowledgeProvider(
                mcp_provider=MCPKnowledgeProvider(settings),
                local_provider=LocalKnowledgeProvider(),
            ),
        )
    return KnowledgeProviderSelection(mode=normalized, provider=LocalKnowledgeProvider())
