# Contributing Guide

This repository uses a GitHub Issue -> branch -> Pull Request workflow.

Process source-of-truth for agents:

- `docs/agent_issue_pr_workflow.md`

## Prerequisites

- `git` installed
- Optional: `gh` (GitHub CLI) for reading issues and creating PRs from terminal

## Standard Flow

0. Confirm feature priority/order and create issue first (required).

1. Sync local `main`:

```bash
git checkout main
git pull --ff-only origin main
```

2. Start work from an issue:

```bash
./scripts/start_issue_branch.sh <issue-number>
```

Example:

```bash
./scripts/start_issue_branch.sh 123
```

3. Implement and verify changes:

```bash
python3 -m unittest discover -s tests -q
```

4. Commit with traceable message:

```bash
git add .
git commit -m "fix: <short summary> (#123)"
```

5. Push branch:

```bash
git push -u origin "$(git branch --show-current)"
```

6. Open PR and link issue:

```bash
gh pr create --fill --base main --head "$(git branch --show-current)"
```

PR description should include `Closes #123` (or `Fixes #123`).

## Optional Full Automation (gh + codex)

If you want one-command automation from issue context to PR:

```bash
./scripts/issue_autopilot.sh 123
```

This command will:

- fetch issue context via `gh`
- create branch `issue/<id>-<slug>`
- run `codex exec` for implementation
- run tests
- commit, push, and create PR

## Branch Naming

- `issue/<id>-<slug>`
- Example: `issue/123-fix-mcp-timeout`

## Review Checklist

- Priority/order confirmed before development
- Issue is linked in PR
- Tests executed and result recorded in PR
- Scope is minimal and aligned to issue goal
