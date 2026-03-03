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
    post_patch_verify_success: bool | None = None
    post_patch_verify_exit_code: int | None = None


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
