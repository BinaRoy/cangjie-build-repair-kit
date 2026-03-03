from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


def run_command(base_dir: Path, args: list[str]) -> str:
    proc = subprocess.run(
        args,
        cwd=base_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def extract_milestone_checklist(source_doc: Path) -> list[tuple[bool, str]]:
    if not source_doc.exists():
        return []
    items: list[tuple[bool, str]] = []
    for raw in source_doc.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("- [ ] "):
            items.append((False, line[6:].strip()))
        elif line.startswith("- [x] "):
            items.append((True, line[6:].strip()))
    return items


def generate_snapshot_markdown(
    timestamp: str,
    branch: str,
    status_short: str,
    latest_commit: str,
    checklist: list[tuple[bool, str]],
    source_doc: Path,
) -> str:
    lines: list[str] = []
    lines.append("# Session Snapshot")
    lines.append("")
    lines.append(f"- generated_at: `{timestamp}`")
    lines.append(f"- source_guide: `{source_doc.as_posix()}`")
    lines.append("")
    lines.append("## Git")
    lines.append(f"- branch: `{branch or 'unknown'}`")
    lines.append(f"- latest_commit: `{latest_commit or 'unknown'}`")
    lines.append("")
    lines.append("### status --short")
    lines.append("```text")
    lines.append(status_short or "(clean)")
    lines.append("```")
    lines.append("")
    lines.append("## Milestone Checklist")
    if checklist:
        for done, text in checklist:
            mark = "x" if done else " "
            lines.append(f"- [{mark}] {text}")
    else:
        lines.append("- no checklist found in source guide")
    lines.append("")
    lines.append("## Next Session Start")
    lines.append("1. Read this file and `docs/development_assessment_and_followup.md`.")
    lines.append("2. Pick the first unchecked P0/P1 task.")
    lines.append("3. Run verification commands before claiming completion.")
    lines.append("")
    return "\n".join(lines)


def write_snapshot_file(base_dir: Path, source_doc: Path, output_path: Path) -> Path:
    timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    branch = run_command(base_dir, ["git", "branch", "--show-current"])
    status_short = run_command(base_dir, ["git", "status", "--short"])
    latest_commit = run_command(base_dir, ["git", "log", "-1", "--pretty=%h %s"])
    checklist = extract_milestone_checklist(source_doc)
    text = generate_snapshot_markdown(
        timestamp=timestamp,
        branch=branch,
        status_short=status_short,
        latest_commit=latest_commit,
        checklist=checklist,
        source_doc=source_doc,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path
