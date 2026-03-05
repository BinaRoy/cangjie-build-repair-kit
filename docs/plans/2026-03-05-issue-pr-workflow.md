# GitHub Issue To PR Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lightweight repository workflow so contributors can start from a GitHub issue, implement changes on a branch, and open a PR with issue traceability.

**Architecture:** Keep the workflow simple and repo-native: contributor guidance in `CONTRIBUTING.md`, issue/PR templates in `.github/`, and one helper script to fetch issue metadata and create a branch. Avoid external services beyond `git` and optional `gh` CLI.

**Tech Stack:** Markdown docs, GitHub templates, Bash script.

---

### Task 1: Define contributor workflow contract

**Files:**
- Create: `CONTRIBUTING.md`
- Modify: `README.md`

1. Write contributor steps: sync main, fetch issue context, create issue branch, implement + test, push + PR.
2. Include exact commands (`git`, optional `gh`) and commit naming convention.
3. Link `CONTRIBUTING.md` from `README.md`.

### Task 2: Add issue and PR templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/improvement.yml`
- Create: `.github/pull_request_template.md`

1. Add structured issue fields for reproduce steps, expected behavior, and impact.
2. Add PR checklist requiring issue link, test evidence, and risk notes.

### Task 3: Add issue bootstrap script

**Files:**
- Create: `scripts/start_issue_branch.sh`

1. Add script to read issue number.
2. If `gh` is available, fetch issue title/body and print summary.
3. Create branch name `issue/<number>-<slug>` from current branch.
4. Print next-step commands for commit and PR creation.

### Task 4: Verify and document usage

**Files:**
- Modify: `docs/git_and_release_workflow.md`

1. Add “Issue -> Branch -> PR” quickstart section.
2. Run shell syntax check for script.
3. Validate git status shows intended file changes only.
