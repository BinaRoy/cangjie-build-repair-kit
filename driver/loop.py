from __future__ import annotations

from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import (
    IterationRecord,
    PolicyConfig,
    ProjectConfig,
    RunSummary,
    to_dict,
)
from driver.state_store import StateStore
from driver.preflight import run_preflight
from knowledge.retriever import retrieve_knowledge
from repair.error_parser import extract_root_cause
from repair.patcher import apply_patch_plan
from repair.planner import propose_patch_plan
from repair.validators import validate_patch_result


def run_loop(
    base_dir: Path,
    run_id: str,
    project: ProjectConfig,
    policy: PolicyConfig,
    adapter: BuildAdapter,
) -> RunSummary:
    store = StateStore(base_dir / "runs", run_id)
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
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
            )
            store.write_iteration(i, to_dict(record))
            final_status = "success"
            stop_reason = "verify_passed"
            break

        error = extract_root_cause((verify.stderr or "") + "\n" + (verify.stdout or ""))
        family_counts[error.family] = family_counts.get(error.family, 0) + 1

        if policy.stop_on_new_error_family and last_error_family and error.family != last_error_family:
            decision = "stop_new_error_family_detected"
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
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
            )
            store.write_iteration(i, to_dict(record))
            stop_reason = decision
            break
        last_error_family = error.family

        if policy.require_root_cause_extracted and error.family == "unknown":
            decision = "stop_root_cause_missing"
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
                post_patch_verify_success=None,
                post_patch_verify_exit_code=None,
            )
            store.write_iteration(i, to_dict(record))
            stop_reason = decision
            break

        knowledge_hits = retrieve_knowledge(base_dir, error)
        if policy.require_knowledge_lookup_on_failure:
            if len(knowledge_hits) < policy.min_knowledge_hits:
                decision = "stop_no_knowledge_hits"
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
                    post_patch_verify_success=None,
                    post_patch_verify_exit_code=None,
                )
                store.write_iteration(i, to_dict(record))
                stop_reason = decision
                break
            if policy.require_knowledge_source_evidence and not _knowledge_sources_valid(base_dir, knowledge_hits):
                decision = "stop_knowledge_source_not_verified"
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
                    post_patch_verify_success=None,
                    post_patch_verify_exit_code=None,
                )
                store.write_iteration(i, to_dict(record))
                stop_reason = decision
                break

        patch_plan = propose_patch_plan(error, knowledge_hits)
        patch_result = apply_patch_plan(patch_plan, project, policy)

        gate_ok, gate_msg = validate_patch_result(patch_result, project, policy, changed_history)
        if patch_result.applied:
            changed_history.update(patch_result.changed_files)

        decision = "continue"
        post_patch_verify_success = None
        post_patch_verify_exit_code = None

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
            post_raw_log = (
                f"$ {post_verify.command}\n\n[stdout]\n{post_verify.stdout}\n\n[stderr]\n{post_verify.stderr}"
            )
            store.write_verify_log(i, post_raw_log, phase="post")
            if not post_verify.success:
                decision = "stop_post_patch_verify_failed"
                stop_reason = decision

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
            post_patch_verify_success=post_patch_verify_success,
            post_patch_verify_exit_code=post_patch_verify_exit_code,
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
