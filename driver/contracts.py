from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class ProjectConfig:
    project_name: str
    project_type: str
    workdir: str
    adapter: str
    verify_command: str
    test_command: str = ""
    command_timeout_sec: int = 600
    editable_paths: list[str] = field(default_factory=list)
    readonly_paths: list[str] = field(default_factory=list)
    artifact_checks: list[str] = field(default_factory=list)
    knowledge_provider: str = "local"
    mcp_server_command: str = ""
    mcp_server_args: list[str] = field(default_factory=list)
    mcp_server_url: str = ""
    mcp_headers: list[str] = field(default_factory=list)
    mcp_tool_name: str = "query-docs"
    mcp_timeout_sec: int = 15
    mcp_max_items: int = 5
    repair_strategy: str = "rule_based"
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_model_secondary: str = ""
    llm_route_rule: str = "error_type_or_complexity"
    llm_secondary_categories: list[str] = field(default_factory=lambda: ["syntax", "generic", "type"])
    llm_complexity_threshold: int = 220
    llm_timeout_sec: int = 30
    llm_temperature: float = 0.0

    def __post_init__(self) -> None:
        mode = (self.knowledge_provider or "local").strip().lower()
        allowed = {"local", "mcp", "hybrid"}
        if mode not in allowed:
            raise ValueError(f"knowledge_provider must be one of {sorted(allowed)}, got: {self.knowledge_provider}")
        self.knowledge_provider = mode
        if self.mcp_timeout_sec <= 0:
            raise ValueError(f"mcp_timeout_sec must be > 0, got: {self.mcp_timeout_sec}")
        if self.mcp_max_items <= 0:
            raise ValueError(f"mcp_max_items must be > 0, got: {self.mcp_max_items}")
        strategy = (self.repair_strategy or "rule_based").strip().lower()
        allowed_strategies = {"rule_based", "llm", "mock_llm", "multi_llm"}
        if strategy not in allowed_strategies:
            raise ValueError(
                f"repair_strategy must be one of {sorted(allowed_strategies)}, got: {self.repair_strategy}"
            )
        self.repair_strategy = strategy
        if self.llm_timeout_sec <= 0:
            raise ValueError(f"llm_timeout_sec must be > 0, got: {self.llm_timeout_sec}")
        route_rule = (self.llm_route_rule or "error_type_or_complexity").strip().lower()
        allowed_rules = {"error_type", "complexity", "error_type_or_complexity"}
        if route_rule not in allowed_rules:
            raise ValueError(f"llm_route_rule must be one of {sorted(allowed_rules)}, got: {self.llm_route_rule}")
        self.llm_route_rule = route_rule
        if self.llm_complexity_threshold <= 0:
            raise ValueError(f"llm_complexity_threshold must be > 0, got: {self.llm_complexity_threshold}")


@dataclass
class PolicyConfig:
    max_iterations: int = 4
    max_files_changed_per_iter: int = 2
    max_total_files_changed: int = 6
    max_changed_lines_per_file: int = 120
    same_error_max_repeat: int = 2
    require_root_cause_extracted: bool = True
    require_diff_summary: bool = True
    stop_on_new_error_family: bool = False
    allow_apply_patch: bool = False
    require_verify_pass_after_patch: bool = True
    require_preflight: bool = True
    require_knowledge_lookup_on_failure: bool = True
    min_knowledge_hits: int = 1
    require_knowledge_source_evidence: bool = True
    require_non_scaffold_patch: bool = True
    min_changed_lines_when_patch_applied: int = 1
    similar_case_top_k: int = 3
    scaffold_markers: list[str] = field(
        default_factory=lambda: ["TODO", "FIXME", "NotImplemented", "stub", "placeholder"]
    )


@dataclass
class VerifyResult:
    success: bool
    exit_code: int
    duration_sec: float
    command: str
    stdout: str
    stderr: str
    artifact_checks: dict[str, bool]


@dataclass
class ErrorBlock:
    family: str
    headline: str
    excerpt: str


@dataclass
class ErrorSchema:
    category: str
    file: str
    line: int | None
    message: str
    context: str
    fingerprint: str

    @property
    def family(self) -> str:
        return self.category

    @property
    def headline(self) -> str:
        return self.message

    @property
    def excerpt(self) -> str:
        return self.context


@dataclass
class KnowledgeItem:
    source: str
    title: str
    content: str


@dataclass
class PatchAction:
    file_path: str
    action: str
    search: str = ""
    replace: str = ""


@dataclass
class PatchPlan:
    can_apply: bool
    rationale: str
    diff_summary: str
    actions: list[PatchAction] = field(default_factory=list)
    referenced_case_ids: list[str] = field(default_factory=list)
    case_match_reason: str = ""


@dataclass
class PatchResult:
    applied: bool
    changed_files: list[str]
    changed_lines_per_file: dict[str, int]
    message: str


@dataclass
class IterationRecord:
    iteration: int
    verify_success: bool
    exit_code: int
    error_family: str
    error_headline: str
    knowledge_hits: list[dict[str, Any]]
    patch_plan: dict[str, Any]
    patch_result: dict[str, Any]
    decision: str
    knowledge_sources: list[str] = field(default_factory=list)
    knowledge_provider_decision: dict[str, Any] = field(default_factory=dict)
    model_route_decision: dict[str, Any] = field(default_factory=dict)
    verify_duration_sec: float | None = None
    post_patch_verify_success: bool | None = None
    post_patch_verify_exit_code: int | None = None
    post_patch_verify_duration_sec: float | None = None


@dataclass
class RunSummary:
    run_id: str
    project_name: str
    iterations: int
    final_status: str
    stop_reason: str


@dataclass
class PreflightResult:
    passed: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


def to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


def normalize_path(path: str, workdir: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path(workdir) / p
    return p.resolve()
