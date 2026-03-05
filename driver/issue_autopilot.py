from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IssueContext:
    number: int
    title: str
    body: str
    url: str
    labels: list[str]


def slugify(text: str) -> str:
    lowered = text.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    collapsed = re.sub(r"-{2,}", "-", collapsed)
    return collapsed or "issue"


def build_branch_name(issue_number: int, issue_title: str) -> str:
    return f"issue/{issue_number}-{slugify(issue_title)}"


def build_tracking_markdown(
    issue: IssueContext,
    branch_name: str,
    base_branch: str,
    test_command: str,
) -> str:
    label_text = ", ".join(issue.labels) if issue.labels else "(none)"
    now = dt.datetime.now().isoformat(timespec="seconds")
    return "\n".join(
        [
            f"# Issue #{issue.number} Development Tracking",
            "",
            f"- Created at: {now}",
            f"- Base branch: `{base_branch}`",
            f"- Working branch: `{branch_name}`",
            f"- Issue URL: {issue.url}",
            f"- Labels: {label_text}",
            f"- Test command: `{test_command}`",
            "",
            "## Issue Context",
            "",
            f"### Title",
            issue.title,
            "",
            "### Body",
            issue.body.strip() or "(empty)",
            "",
            "## Execution Log",
            "",
            "- [ ] Issue context fetched",
            "- [ ] Codex modifications completed",
            "- [ ] Tests executed",
            "- [ ] Commit pushed",
            "- [ ] PR created",
            "",
        ]
    )


def build_pr_body(issue: IssueContext, test_command: str, tracking_file: str) -> str:
    return "\n".join(
        [
            f"Closes #{issue.number}",
            "",
            "## Summary",
            f"- Auto-generated from issue context: {issue.url}",
            "",
            "## Validation",
            f"- Command: `{test_command}`",
            "- Result: (filled by automation run logs)",
            "",
            "## Tracking",
            f"- Development log: `{tracking_file}`",
        ]
    )


def _run(cmd: list[str], cwd: Path, capture_output: bool = False) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture_output,
    )
    if capture_output:
        return result.stdout.strip()
    return ""


def _run_shell(command: str, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, text=True, shell=True)


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required tool not found: {name}")


def _fetch_issue(issue_number: int, cwd: Path) -> IssueContext:
    raw = _run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,title,body,url,labels",
        ],
        cwd=cwd,
        capture_output=True,
    )
    data = json.loads(raw)
    labels = [item.get("name", "").strip() for item in data.get("labels", []) if item.get("name")]
    return IssueContext(
        number=int(data["number"]),
        title=str(data["title"]),
        body=str(data.get("body", "")),
        url=str(data["url"]),
        labels=labels,
    )


def _append_tracking_log(path: Path, line: str) -> None:
    ts = dt.datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {ts} {line}\n")


def run_issue_autopilot(
    issue_number: int,
    base_branch: str = "main",
    test_command: str = "python3 -m unittest discover -s tests -q",
    run_codex: bool = True,
    create_pr: bool = True,
    push_branch: bool = True,
) -> int:
    cwd = Path.cwd()
    _require_tool("git")
    _require_tool("gh")
    if run_codex:
        _require_tool("codex")

    issue = _fetch_issue(issue_number, cwd)
    branch_name = build_branch_name(issue.number, issue.title)

    _run(["git", "checkout", base_branch], cwd=cwd)
    _run(["git", "pull", "--ff-only", "origin", base_branch], cwd=cwd)
    _run(["git", "checkout", "-b", branch_name], cwd=cwd)

    tracking_dir = cwd / "docs" / "dev-tracking"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    tracking_file = tracking_dir / f"issue-{issue.number}-{slugify(issue.title)}.md"
    tracking_file.write_text(
        build_tracking_markdown(
            issue=issue,
            branch_name=branch_name,
            base_branch=base_branch,
            test_command=test_command,
        ),
        encoding="utf-8",
    )
    _append_tracking_log(tracking_file, "Issue context fetched")

    if run_codex:
        prompt = "\n".join(
            [
                f"Please implement GitHub issue #{issue.number} in this repository.",
                f"Issue title: {issue.title}",
                "Issue body:",
                issue.body or "(empty)",
                "",
                "Requirements:",
                "- Make the minimal code changes needed to resolve the issue.",
                f"- Update `{tracking_file.as_posix()}` with what changed and why.",
                "- Run project tests and keep changes scoped to the issue.",
            ]
        )
        subprocess.run(["codex", "exec", prompt], cwd=cwd, check=True, text=True)
        _append_tracking_log(tracking_file, "Codex modifications completed")
    else:
        _append_tracking_log(tracking_file, "Codex execution skipped by flag")

    _run_shell(test_command, cwd=cwd)
    _append_tracking_log(tracking_file, f"Tests executed: `{test_command}`")

    commit_title = f"fix: resolve issue #{issue.number} - {slugify(issue.title)}"
    _run(["git", "add", "-A"], cwd=cwd)
    _run(["git", "commit", "-m", commit_title], cwd=cwd)
    _append_tracking_log(tracking_file, f"Committed changes: `{commit_title}`")

    if push_branch:
        _run(["git", "push", "-u", "origin", branch_name], cwd=cwd)
        _append_tracking_log(tracking_file, f"Pushed branch: `{branch_name}`")
    else:
        _append_tracking_log(tracking_file, "Push skipped by flag")

    if create_pr:
        pr_body = build_pr_body(issue, test_command=test_command, tracking_file=tracking_file.as_posix())
        _run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                base_branch,
                "--head",
                branch_name,
                "--title",
                f"fix: {issue.title} (#{issue.number})",
                "--body",
                pr_body,
            ],
            cwd=cwd,
        )
        _append_tracking_log(tracking_file, "PR created")
    else:
        _append_tracking_log(tracking_file, "PR creation skipped by flag")

    print(f"issue-autopilot complete: issue #{issue.number}, branch {branch_name}")
    return 0
