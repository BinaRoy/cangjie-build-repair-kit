from __future__ import annotations

import json
from pathlib import Path


def generate_run_report(run_dir: Path) -> Path:
    summary = _read_json(run_dir / "summary.json")
    preflight = _read_json(run_dir / "preflight.json")
    iterations = sorted(run_dir.glob("iter_*.json"))
    records = [_read_json(p) for p in iterations]

    lines: list[str] = []
    lines.append(f"# Run Report: {summary.get('run_id', run_dir.name)}")
    lines.append("")
    lines.append("## Result")
    lines.append(f"- project: `{summary.get('project_name', '')}`")
    lines.append(f"- status: `{summary.get('final_status', '')}`")
    lines.append(f"- stop_reason: `{summary.get('stop_reason', '')}`")
    lines.append(f"- iterations: `{summary.get('iterations', 0)}`")
    lines.append("")

    if preflight:
        lines.append("## Preflight")
        lines.append(f"- passed: `{preflight.get('passed')}`")
        lines.append(f"- reason: `{preflight.get('reason', '')}`")
        details = preflight.get("details", {})
        if isinstance(details, dict):
            if details.get("hint"):
                lines.append(f"- hint: {details['hint']}")
            remediation = details.get("remediation")
            if isinstance(remediation, list) and remediation:
                lines.append("- remediation:")
                for item in remediation:
                    lines.append(f"  - {item}")
        lines.append("")

    lines.append("## Iterations")
    if not records:
        lines.append("- no iteration records")
    else:
        for rec in records:
            lines.append(
                f"- iter={rec.get('iteration')} verify_success={rec.get('verify_success')} "
                f"decision={rec.get('decision')} error_family={rec.get('error_family')}"
            )
            if rec.get("knowledge_hits"):
                sources = [x.get("source", "") for x in rec["knowledge_hits"] if isinstance(x, dict)]
                if sources:
                    lines.append(f"  - knowledge_sources: {', '.join(sources)}")

    path = run_dir / "report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
