# Agent Stable Issue-PR Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure agents can execute a stable, repository-driven Issue->Dev->PR workflow without relying on chat context.

**Architecture:** Add one source-of-truth workflow document for agents, then reinforce it through issue/PR templates and contributing docs.

**Tech Stack:** Markdown docs + GitHub templates + gh CLI install.

---

### Task 1: Add source-of-truth workflow document
- Create `docs/agent_issue_pr_workflow.md`
- Include strict sequence: priority confirmation -> issue creation -> issue branch -> implementation -> tests -> PR.
- Include both manual and autopilot commands.

### Task 2: Reinforce workflow in templates and docs
- Modify `.github/ISSUE_TEMPLATE/improvement.yml` with priority/order fields.
- Modify `.github/pull_request_template.md` to require priority confirmation and issue linkage.
- Modify `CONTRIBUTING.md` and `README.md` to point to the workflow doc.

### Task 3: Install and verify gh CLI
- Install `gh` using system package manager.
- Verify with `gh --version`.
- Note login prerequisite (`gh auth login`).

### Task 4: Verification
- Run repository tests.
- Report changed files and usage instructions.
