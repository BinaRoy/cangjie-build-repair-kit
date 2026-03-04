from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


def generate_weekly_comparison_report(runs_dir: Path, output_path: Path, days: int = 7) -> Path:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    rows: dict[str, dict[str, Any]] = {}

    for run_dir in sorted(runs_dir.glob("*")):
        if not run_dir.is_dir():
            continue
        run_ts = _parse_run_time(run_dir.name)
        if run_ts is None or run_ts < cutoff:
            continue
        summary = _read_json(run_dir / "summary.json")
        if not summary:
            continue
        records = [_read_json(p) for p in sorted(run_dir.glob("iter_*.json"))]
        route_model = _route_model_from_records(records)
        stat = rows.setdefault(
            route_model,
            {"runs": 0, "success": 0, "iterations": 0, "duration": 0.0, "safety_events": 0},
        )
        stat["runs"] += 1
        if str(summary.get("final_status", "")) == "success":
            stat["success"] += 1
        stat["iterations"] += int(summary.get("iterations", 0))
        stat["duration"] += _sum_duration(records)
        stat["safety_events"] += _count_safety_events(records)

    lines: list[str] = []
    lines.append("# Weekly Model Comparison Report")
    lines.append("")
    lines.append("| model | runs | success_rate | avg_iterations | avg_duration_sec | safety_events |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for model, stat in sorted(rows.items()):
        runs = int(stat["runs"])
        success_rate = (float(stat["success"]) / runs * 100.0) if runs else 0.0
        avg_iter = (float(stat["iterations"]) / runs) if runs else 0.0
        avg_duration = (float(stat["duration"]) / runs) if runs else 0.0
        lines.append(
            f"| {model} | {runs} | {success_rate:.1f}% | {avg_iter:.2f} | {avg_duration:.2f} | {int(stat['safety_events'])} |"
        )
    if len(rows) == 0:
        lines.append("| n/a | 0 | 0.0% | 0.00 | 0.00 | 0 |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _parse_run_time(run_id: str) -> dt.datetime | None:
    # Format: YYYYMMDD_HHMMSS_mmm_xxxxxx
    try:
        return dt.datetime.strptime(run_id[:15], "%Y%m%d_%H%M%S")
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        out = json.loads(path.read_text(encoding="utf-8"))
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _route_model_from_records(records: list[dict[str, Any]]) -> str:
    for rec in records:
        route = rec.get("model_route_decision", {})
        if isinstance(route, dict):
            model = str(route.get("selected_model", "")).strip()
            if model:
                return model
    return "non_routed"


def _sum_duration(records: list[dict[str, Any]]) -> float:
    total = 0.0
    for rec in records:
        total += float(rec.get("verify_duration_sec", 0.0) or 0.0)
        total += float(rec.get("post_patch_verify_duration_sec", 0.0) or 0.0)
    return total


def _count_safety_events(records: list[dict[str, Any]]) -> int:
    cnt = 0
    for rec in records:
        decision = str(rec.get("decision", ""))
        if decision.startswith("stop_policy_gate_failed"):
            cnt += 1
        elif decision in {
            "stop_strategy_direct_write_detected",
            "stop_knowledge_source_not_verified",
            "stop_new_error_family_detected",
        }:
            cnt += 1
    return cnt
