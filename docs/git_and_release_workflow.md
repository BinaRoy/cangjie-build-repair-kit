# Git And Release Workflow

## Build product package

PowerShell:

```powershell
./scripts/build_release.ps1
```

Output:
- `release/product_bundle.zip` (recommended to share/upload)

## Git initialization (first time)

```powershell
git init
git add .
git commit -m "init: cangjie repair tool with product export"
```

## Connect remote and push

```powershell
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Update workflow

```powershell
# code changes
./scripts/build_release.ps1
git add .
git commit -m "feat: ..."
git push
```

## Issue -> Branch -> PR workflow

Before coding a new feature:

- Confirm feature priority/order with owner
- Create or update a GitHub issue
- Follow `docs/agent_issue_pr_workflow.md`

```bash
git checkout main
git pull --ff-only origin main
./scripts/start_issue_branch.sh <issue-number>
```

Then:

```bash
# implement and verify
python3 -m unittest discover -s tests -q
git add .
git commit -m "fix: <summary> (#<issue-number>)"
git push -u origin "$(git branch --show-current)"
gh pr create --fill --base main --head "$(git branch --show-current)"
```

PR body should include `Closes #<issue-number>`.

## One-command autopilot (gh CLI mode)

Prerequisites:

- `gh` is installed and authenticated (`gh auth status`)
- `codex` is installed

Run:

```bash
./scripts/issue_autopilot.sh <issue-number>
```

Useful flags:

```bash
# skip code generation, only branch + tracking + test + git/pr flow
./scripts/issue_autopilot.sh <issue-number> --skip-codex

# do not push and do not create PR
./scripts/issue_autopilot.sh <issue-number> --no-push --no-pr
```
