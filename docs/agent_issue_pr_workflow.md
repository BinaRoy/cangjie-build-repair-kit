# Agent Issue-PR Workflow (Source of Truth)

This document defines the required workflow for any agent working in this repository.
Do not rely on chat context as process memory. Follow this file.

## Mandatory Order

1. Confirm feature priority order.
2. Create or update the corresponding GitHub issue.
3. Start development from that issue.
4. Implement minimal scoped changes.
5. Run tests.
6. Open PR linked to the issue.

Development without an issue is out-of-process.

## Step 1: Confirm Priority Before Development

Before any new feature work:

- Identify candidate features.
- Confirm the implementation order with project owner.
- Ensure each feature has one issue.

Recommended issue metadata:

- Priority: `P0` / `P1` / `P2`
- Order in queue: integer (`1`, `2`, ...)
- Blockers / dependencies

## Step 2: Create or Prepare Issue

Create an issue first using GitHub templates.

Requirements:

- Clear goal and acceptance criteria
- Priority and order fields filled
- Enough context for implementation without chat history

## Step 3: Start Branch From Issue

Manual:

```bash
git checkout main
git pull --ff-only origin main
./scripts/start_issue_branch.sh <issue-number>
```

Automated:

```bash
./scripts/issue_autopilot.sh <issue-number>
```

## Step 4: Implement and Track Changes

While developing:

- Keep changes scoped to issue acceptance criteria.
- Keep development tracking under `docs/dev-tracking/`.
- Record key decisions, commands, and results in tracking doc.

## Step 5: Verify

Default test command:

```bash
python3 -m unittest discover -s tests -q
```

No completion claim before fresh test evidence.

## Step 6: Submit PR

PR must include:

- `Closes #<issue-number>`
- Test evidence
- Risk and rollback notes
- Confirmation that priority was validated before development

## Quick Commands

Manual flow:

```bash
./scripts/start_issue_branch.sh 123
python3 -m unittest discover -s tests -q
git add .
git commit -m "fix: <summary> (#123)"
git push -u origin "$(git branch --show-current)"
gh pr create --fill --base main --head "$(git branch --show-current)"
```

Autopilot flow:

```bash
./scripts/issue_autopilot.sh 123
```
