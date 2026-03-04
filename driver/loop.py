from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from adapters.base import BuildAdapter
from driver.contracts import (
    ErrorSchema,
    IterationRecord,
    PatchPlan,
    PatchResult,
    PolicyConfig,
    ProjectConfig,
    RunSummary,
    to_dict,
)
from driver.failure_cases import FailureCaseStore, create_failure_case_record
from driver.state_store import StateStore
from driver.preflight import run_preflight
from knowledge.providers import resolve_knowledge_provider_for_project
from repair.error_parser import extract_root_cause
from repair.patcher import apply_patch_plan
from repair.strategies.mock_llm import MockLLMStrategy
from repair.strategies.multi_llm import MultiModelLLMStrategy
from repair.strategies.real_llm import RealLLMStrategy
from repair.strategies.rule_based import RuleBasedStrategy
from repair.validators import validate_patch_result


class StrategyProtocol(Protocol):
    def propose(self, error: ErrorSchema, context: Any) -> PatchPlan:
        raise NotImplementedError


def run_loop(
    base_dir: Path,
    run_id: str,
    project: ProjectConfig,
    policy: PolicyConfig,
    adapter: BuildAdapter,
    parser: Callable[[str], ErrorSchema] = extract_root_cause,
    strategy: StrategyProtocol | None = None,
    applier: Callable[[PatchPlan, ProjectConfig, PolicyConfig], PatchResult] = apply_patch_plan,
    verifier: Callable[[PatchResult, ProjectConfig, PolicyConfig, set[str]], tuple[bool, str]] = validate_patch_result,
) -> RunSummary:
    store = StateStore(base_dir / "runs", run_id)
    failure_case_store = FailureCaseStore(base_dir)
    active_strategy = strategy or _build_default_strategy(project)
    knowledge_provider_selection = resolve_knowledge_provider_for_project(project.knowledge_provider, project)
    if policy.require_preflight:
        preflight = run_preflight(project)
        store.write_preflight(to_dict(preflight))
        if not preflight.passed:
            summary = RunSummary(
                run_id=run_id,
                project_name=project.project_name,
                iterations=0,
                final_status="failed",
                stop_reason=f"preflight_failed:{preflight.reason}",
            )
            store.write_summary(to_dict(summary))
            return summary

    changed_history: set[str] = set()
    family_counts: dict[str, int] = {}
    last_error_family: str | None = None

    final_status = "failed"
    stop_reason = "max_iterations_reached"
    iterations_done = 0

    for i in range(1, policy.max_iterations + 1):
        iterations_done = i
        verify = adapter.verify(project)
        raw_log = f"$ {verify.command}\n\n[stdout]\n{verify.stdout}\n\n[stderr]\n{verify.stderr}"
        store.write_verify_log(i, raw_log, phase="pre")

        if verify.success:
            record = IterationRecord(
                iteration=i,
                verify_success=True,
                exit_code=verify.exit_code,
                error_family="none",
                error_headline="build passed",
                knowledge_hits=[],
                patch_plan={},
                patch_result={},
                decision="done_success",
                model_route_decision={},
                verify_duration_sec=verify.duration_sec,
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
                post_patch_verify_duration_sec=None,
            )
            store.write_iteration(i, to_dict(record))
            final_status = "success"
            stop_reason = "verify_passed"
            break

        error = parser((verify.stderr or "") + "\n" + (verify.stdout or ""))
        store.write_error(i, to_dict(error))
        empty_patch_plan = {
            "can_apply": False,
            "rationale": "No patch generated because loop stopped before planning.",
            "diff_summary": "No patch generated.",
            "actions": [],
        }
        family_counts[error.family] = family_counts.get(error.family, 0) + 1

        if policy.stop_on_new_error_family and last_error_family and error.family != last_error_family:
            store.write_patch_plan(i, empty_patch_plan)
            decision = "stop_new_error_family_detected"
            _archive_failure_case(
                failure_case_store=failure_case_store,
                error=error,
                knowledge_hits=[],
                patch_plan=empty_patch_plan,
                patch_result={},
                decision=decision,
                run_id=run_id,
                iteration=i,
            )
            record = IterationRecord(
                iteration=i,
                verify_success=False,
                exit_code=verify.exit_code,
                error_family=error.family,
                error_headline=error.headline,
                knowledge_hits=[],
                patch_plan={},
                patch_result={},
                decision=decision,
                model_route_decision={},
                verify_duration_sec=verify.duration_sec,
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
                post_patch_verify_duration_sec=None,
            )
            store.write_iteration(i, to_dict(record))
            stop_reason = decision
            break
        last_error_family = error.family

        if policy.require_root_cause_extracted and error.family == "unknown":
            store.write_patch_plan(i, empty_patch_plan)
            decision = "stop_root_cause_missing"
            _archive_failure_case(
                failure_case_store=failure_case_store,
                error=error,
                knowledge_hits=[],
                patch_plan=empty_patch_plan,
                patch_result={},
                decision=decision,
                run_id=run_id,
                iteration=i,
            )
            record = IterationRecord(
                iteration=i,
                verify_success=False,
                exit_code=verify.exit_code,
                error_family=error.family,
                error_headline=error.headline,
                knowledge_hits=[],
                patch_plan={},
                patch_result={},
                decision=decision,
                model_route_decision={},
                verify_duration_sec=verify.duration_sec,
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
                post_patch_verify_duration_sec=None,
            )
            store.write_iteration(i, to_dict(record))
            stop_reason = decision
            break

        knowledge_hits = knowledge_provider_selection.provider.retrieve(base_dir, error)
        similar_cases = failure_case_store.find_similar_cases(error.fingerprint, top_k=policy.similar_case_top_k)
        knowledge_sources = _extract_knowledge_sources(knowledge_hits)
        knowledge_provider_decision = _build_knowledge_provider_decision(
            knowledge_provider_selection.mode,
            knowledge_provider_selection.provider.name,
            knowledge_provider_selection.provider,
            len(knowledge_hits),
        )
        if policy.require_knowledge_lookup_on_failure:
            if len(knowledge_hits) < policy.min_knowledge_hits:
                store.write_patch_plan(i, empty_patch_plan)
                decision = "stop_no_knowledge_hits"
                _archive_failure_case(
                    failure_case_store=failure_case_store,
                    error=error,
                    knowledge_hits=[to_dict(x) for x in knowledge_hits],
                    patch_plan=empty_patch_plan,
                    patch_result={},
                    decision=decision,
                    run_id=run_id,
                    iteration=i,
                )
                record = IterationRecord(
                    iteration=i,
                    verify_success=False,
                    exit_code=verify.exit_code,
                    error_family=error.family,
                    error_headline=error.headline,
                    knowledge_hits=[to_dict(x) for x in knowledge_hits],
                    patch_plan={},
                    patch_result={},
                    decision=decision,
                    knowledge_sources=knowledge_sources,
                    knowledge_provider_decision=knowledge_provider_decision,
                    model_route_decision={},
                    verify_duration_sec=verify.duration_sec,
                    post_patch_verify_success=None,
                    post_patch_verify_exit_code=None,
                    post_patch_verify_duration_sec=None,
                )
                store.write_iteration(i, to_dict(record))
                stop_reason = decision
                break
            if policy.require_knowledge_source_evidence and not _knowledge_sources_valid(base_dir, knowledge_hits):
                store.write_patch_plan(i, empty_patch_plan)
                decision = "stop_knowledge_source_not_verified"
                _archive_failure_case(
                    failure_case_store=failure_case_store,
                    error=error,
                    knowledge_hits=[to_dict(x) for x in knowledge_hits],
                    patch_plan=empty_patch_plan,
                    patch_result={},
                    decision=decision,
                    run_id=run_id,
                    iteration=i,
                )
                record = IterationRecord(
                    iteration=i,
                    verify_success=False,
                    exit_code=verify.exit_code,
                    error_family=error.family,
                    error_headline=error.headline,
                    knowledge_hits=[to_dict(x) for x in knowledge_hits],
                    patch_plan={},
                    patch_result={},
                    decision=decision,
                    knowledge_sources=knowledge_sources,
                    knowledge_provider_decision=knowledge_provider_decision,
                    model_route_decision={},
                    verify_duration_sec=verify.duration_sec,
                    post_patch_verify_success=None,
                    post_patch_verify_exit_code=None,
                    post_patch_verify_duration_sec=None,
                )
                store.write_iteration(i, to_dict(record))
                stop_reason = decision
                break

        strategy_context = {
            "knowledge_hits": knowledge_hits,
            "similar_cases": similar_cases,
            "iteration": i,
            "run_id": run_id,
            "project_name": project.project_name,
            "knowledge_provider_mode": knowledge_provider_selection.mode,
            "knowledge_provider_name": knowledge_provider_selection.provider.name,
            "knowledge_sources": knowledge_sources,
            "knowledge_provider_decision": knowledge_provider_decision,
        }
        before_strategy_files = _snapshot_editable_files(project)
        patch_plan = active_strategy.propose(error, strategy_context)
        model_route_decision = _extract_model_route_decision(active_strategy)
        _attach_case_references_to_patch_plan(patch_plan, similar_cases)
        after_strategy_files = _snapshot_editable_files(project)
        if before_strategy_files != after_strategy_files:
            _restore_editable_files(before_strategy_files, after_strategy_files)
            store.write_patch_plan(i, empty_patch_plan)
            decision = "stop_strategy_direct_write_detected"
            _archive_failure_case(
                failure_case_store=failure_case_store,
                error=error,
                knowledge_hits=[to_dict(x) for x in knowledge_hits],
                patch_plan=empty_patch_plan,
                patch_result={},
                decision=decision,
                run_id=run_id,
                iteration=i,
            )
            record = IterationRecord(
                iteration=i,
                verify_success=False,
                exit_code=verify.exit_code,
                error_family=error.family,
                error_headline=error.headline,
                knowledge_hits=[to_dict(x) for x in knowledge_hits],
                patch_plan={},
                patch_result={},
                decision=decision,
                knowledge_sources=knowledge_sources,
                knowledge_provider_decision=knowledge_provider_decision,
                model_route_decision=model_route_decision,
                verify_duration_sec=verify.duration_sec,
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
                post_patch_verify_duration_sec=None,
            )
            store.write_iteration(i, to_dict(record))
            stop_reason = decision
            break
        store.write_patch_plan(i, to_dict(patch_plan))
        patch_result = applier(patch_plan, project, policy)

        gate_ok, gate_msg = verifier(patch_result, project, policy, changed_history)
        if patch_result.applied:
            changed_history.update(patch_result.changed_files)

        decision = "continue"
        post_patch_verify_success = None
        post_patch_verify_exit_code = None
        post_patch_verify_duration_sec = None

        if family_counts[error.family] > policy.same_error_max_repeat:
            decision = "stop_same_error_repeated"
            stop_reason = decision
        elif not gate_ok:
            decision = "stop_policy_gate_failed"
            stop_reason = f"{decision}:{gate_msg}"
        elif policy.require_diff_summary and not patch_plan.diff_summary:
            decision = "stop_missing_diff_summary"
            stop_reason = decision
        elif not patch_result.applied:
            decision = "stop_patch_disabled_by_policy" if not policy.allow_apply_patch else "stop_no_patch_applied"
            stop_reason = decision
        elif policy.require_verify_pass_after_patch:
            post_verify = adapter.verify(project)
            post_patch_verify_success = post_verify.success
            post_patch_verify_exit_code = post_verify.exit_code
            post_patch_verify_duration_sec = post_verify.duration_sec
            post_raw_log = (
                f"$ {post_verify.command}\n\n[stdout]\n{post_verify.stdout}\n\n[stderr]\n{post_verify.stderr}"
            )
            store.write_verify_log(i, post_raw_log, phase="post")
            if not post_verify.success:
                decision = "stop_post_patch_verify_failed"
                stop_reason = decision

        _archive_failure_case(
            failure_case_store=failure_case_store,
            error=error,
            knowledge_hits=[to_dict(x) for x in knowledge_hits],
            patch_plan=to_dict(patch_plan),
            patch_result=to_dict(patch_result),
            decision=decision,
            run_id=run_id,
            iteration=i,
        )

        record = IterationRecord(
            iteration=i,
            verify_success=False,
            exit_code=verify.exit_code,
            error_family=error.family,
            error_headline=error.headline,
            knowledge_hits=[to_dict(x) for x in knowledge_hits],
            patch_plan=to_dict(patch_plan),
            patch_result=to_dict(patch_result),
            decision=decision,
            knowledge_sources=knowledge_sources,
            knowledge_provider_decision=knowledge_provider_decision,
            model_route_decision=model_route_decision,
            verify_duration_sec=verify.duration_sec,
            post_patch_verify_success=post_patch_verify_success,
            post_patch_verify_exit_code=post_patch_verify_exit_code,
            post_patch_verify_duration_sec=post_patch_verify_duration_sec,
        )
        store.write_iteration(i, to_dict(record))

        if decision != "continue":
            break

    summary = RunSummary(
        run_id=run_id,
        project_name=project.project_name,
        iterations=iterations_done,
        final_status=final_status,
        stop_reason=stop_reason,
    )
    store.write_summary(to_dict(summary))
    return summary


def _build_default_strategy(project: ProjectConfig) -> StrategyProtocol:
    if project.repair_strategy == "multi_llm":
        return MultiModelLLMStrategy(
            api_url=project.llm_api_url,
            api_key=project.llm_api_key,
            model_primary=project.llm_model,
            model_secondary=project.llm_model_secondary or project.llm_model,
            route_rule=project.llm_route_rule,
            secondary_categories=list(project.llm_secondary_categories),
            complexity_threshold=project.llm_complexity_threshold,
            timeout_sec=project.llm_timeout_sec,
            temperature=project.llm_temperature,
        )
    if project.repair_strategy == "llm":
        return RealLLMStrategy.from_project_config(project)
    if project.repair_strategy == "mock_llm":
        return MockLLMStrategy()
    return RuleBasedStrategy()


def _knowledge_sources_valid(base_dir: Path, hits: list) -> bool:
    for hit in hits:
        src = getattr(hit, "source", "")
        if not src:
            return False
        # External URLs are not used in this template; require local evidence file.
        if src.startswith("http://") or src.startswith("https://"):
            return False
        path = (base_dir / src).resolve()
        if not path.exists():
            return False
    return True


def _extract_knowledge_sources(hits: list) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        src = str(getattr(hit, "source", "")).strip()
        if not src or src in seen:
            continue
        seen.add(src)
        sources.append(src)
    return sources


def _build_knowledge_provider_decision(
    mode: str,
    provider_name: str,
    provider: Any,
    hit_count: int,
) -> dict[str, Any]:
    decision = {
        "configured_mode": mode,
        "provider_name": provider_name,
        "hit_count": hit_count,
    }
    getter = getattr(provider, "get_last_decision", None)
    if callable(getter):
        extra = getter()
        if isinstance(extra, dict):
            decision.update(extra)
    return decision


def _extract_model_route_decision(strategy: StrategyProtocol) -> dict[str, Any]:
    getter = getattr(strategy, "get_last_route_decision", None)
    if callable(getter):
        out = getter()
        if isinstance(out, dict):
            return dict(out)
    return {}


def _archive_failure_case(
    *,
    failure_case_store: FailureCaseStore,
    error: ErrorSchema,
    knowledge_hits: list[dict[str, Any]],
    patch_plan: dict[str, Any],
    patch_result: dict[str, Any],
    decision: str,
    run_id: str,
    iteration: int,
) -> None:
    record = create_failure_case_record(
        fingerprint=error.fingerprint,
        context={
            "error": to_dict(error),
            "knowledge_hits": knowledge_hits,
        },
        plan=patch_plan,
        result={
            "decision": decision,
            "patch_result": patch_result,
        },
        run_id=run_id,
        iteration=iteration,
    )
    failure_case_store.write_case_dedup(record)


def _attach_case_references_to_patch_plan(patch_plan: PatchPlan, similar_cases: list[dict[str, Any]]) -> None:
    if getattr(patch_plan, "referenced_case_ids", None):
        return
    ids: list[str] = []
    reason_parts: list[str] = []
    for row in similar_cases:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        ids.append(case_id)
        score = row.get("score", "")
        reason_parts.append(f"{case_id}(score={score})")
    patch_plan.referenced_case_ids = ids
    patch_plan.case_match_reason = (
        f"Top similar cases from fingerprint retrieval: {', '.join(reason_parts)}" if reason_parts else ""
    )


def _snapshot_editable_files(project: ProjectConfig) -> dict[Path, str]:
    workdir = Path(project.workdir).resolve()
    snapshots: dict[Path, str] = {}
    for rel_root in project.editable_paths:
        root = (workdir / rel_root).resolve()
        if not root.exists():
            continue
        if root.is_file():
            snapshots[root] = root.read_text(encoding="utf-8", errors="replace")
            continue
        for path in root.rglob("*"):
            if path.is_file():
                snapshots[path.resolve()] = path.read_text(encoding="utf-8", errors="replace")
    return snapshots


def _restore_editable_files(before: dict[Path, str], after: dict[Path, str]) -> None:
    # Remove files created during strategy execution.
    for path in after:
        if path not in before and path.exists():
            path.unlink()
    # Restore previous contents for modified/deleted files.
    for path, content in before.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
