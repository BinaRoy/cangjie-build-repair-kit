# Cangjie Build-Repair Kit: Project Overview and Progress

## Contributor workflow

- PR-based development guide: `CONTRIBUTING.md`
- Agent workflow source-of-truth: `docs/agent_issue_pr_workflow.md`
- Release/build notes: `docs/git_and_release_workflow.md`
- Issue autopilot entry: `scripts/issue_autopilot.sh`
- MVP safe-mode behavior and repair-enabling guide: `docs/mvp_safe_mode_and_repairing.md`

## 1. What problem this project solves

In Cangjie projects, using an LLM or an agent to write code is usually not the hard part. The real time cost is debugging and verification after code changes.

The repeated loop is simple: run build, read errors, edit code, run build again. But across different projects (UI / non-UI), commands, directories, and constraints are different. This makes the process hard to reuse and hard to audit. Also, fully free-form AI debugging is often too divergent and loses context.  
So this project turns that loop into a reusable engineering workflow:

`Build -> Diagnose -> Plan -> Patch -> Verify -> Record`

Core boundaries:

- Project differences are handled by config (commands, workdir, editable paths, artifact checks).
- Strategy and execution are separated (strategy only proposes a plan; PatchApplier applies changes).
- Every iteration produces structured artifacts for troubleshooting and regression.

---

## 2. Current progress (already implemented)

### 2.1 Main flow and modules

- Main loop: `driver/loop.py`
- Build adapters: `adapters/cjpm_adapter.py`, `adapters/hvigor_adapter.py`
- Unified verification: `driver/verifier.py` (build/test/artifact)
- Error parsing: `repair/error_parser.py` (with stable fingerprint)
- Patch execution: `repair/patcher.py` (dry-run, rollback on failure, path/line limits)
- Strategy interface: `repair/strategies/base.py`
- Rule strategy: `repair/strategies/rule_based.py`
- LLM protocol and providers: `repair/strategies/llm.py`, `repair/strategies/real_llm.py`, `repair/strategies/multi_llm.py`
- Knowledge provider layer: `knowledge/providers.py`, `knowledge/mcp_provider.py`
- Failure case memory: `driver/failure_cases.py`
- Weekly model report: `driver/weekly_report.py`

### 2.2 Auditable outputs

Each run creates files under `runs/<run_id>/`:

- `error_iter_<n>.json`
- `patch_plan_iter_<n>.json`
- `iter_<n>.json`
- `verify_iter_<n>.log`
- `patch_iter_<n>.diff`
- `summary.json`
- `report.md`

These are structured outputs (fixed fields in JSON/Markdown), not only raw logs. This makes search, comparison, and regression tracking easier.

### 2.3 Current verification baseline

At current working baseline:

- Test command: `python3 -m unittest discover -s tests -q`
- Latest result: `Ran 75 tests ... OK`

So the current version is already usable as a runnable, verifiable, and traceable repair framework.

---

## 3. Next plan (adjusted to current conditions)

Since usable MCP options are already available, the order is:
MCP first, then real LLM, then multi-model expansion.

### Phase 1: Integrate MCP first 

Goals:

- Implement provider mode in `knowledge`: `local | mcp | hybrid`.
- Connect available MCP and complete the chain: error context -> knowledge retrieval -> structured output.
- Keep local fallback to avoid MCP instability breaking the run.

Delivery criteria:

- The same error can return traceable sources in both local and mcp modes (`source` is checkable).
- If MCP is unavailable, the run automatically falls back to local mode and continues.

### Phase 2: Integrate a real LLM 

Goals:

- Replace `MockLLMStrategy` with a real model integration.
- Use MCP/local retrieval results as default input to reduce unsupported edits.
- Keep the rule: model outputs `PatchPlan` only; it cannot write files directly.

Delivery criteria:

- On at least one non-UI sample where rule strategy cannot fix the issue, LLM strategy provides an executable patch plan.
- Audit artifacts are fully persisted (error / patch_plan / diff / summary).

### Phase 3: Multi-model expansion 

Goals:

- Support model routing in strategy layer (by error type or complexity).
- Keep routing rules minimal; no heavy orchestration.

Delivery criteria:

- At least two model providers can be configured and switched.
- The same input can reproduce routing decisions and recorded outputs.

---

## 4. How to try it on a project (practical steps)

### 4.1 First-time setup for a new project

Recommended path (faster and safer): use bootstrap command.

1. Bootstrap configs and follow guide:

```bash
python3 -m driver.main bootstrap-nonui --project-root /path/to/project --output-dir ./my-configs --project-name myproj
```

This generates:

- `project.myproj.toml`
- `policy.default.toml`
- `FOLLOW_GUIDE.md` (step-by-step commands for validate/run/inspect)

2. If the project does not contain `cjpm.toml`, fill `verify_command` manually in `project.myproj.toml`.

3. Validate command/path availability:

```bash
python3 -m driver.main validate --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

4. Run one full loop:

```bash
python3 -m driver.main run --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

5. Check `runs/<run_id>/summary.json` and `report.md` to confirm success, failure, or safe stop.

Alternative (manual template init):

1. Generate config:

```bash
python3 -m driver.main init --template non_ui --output-dir ./my-configs --project-name myproj --workdir /path/to/project
```

2. Update 4 key fields in config: `verify_command`, `test_command`, `editable_paths`, `artifact_checks`.

3. Validate command/path availability:

```bash
python3 -m driver.main validate --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

4. Run one full loop:

```bash
python3 -m driver.main run --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

5. Check `runs/<run_id>/summary.json` and `report.md` to confirm success, failure, or safe stop.

### 4.4 What an agent can auto-configure

With this repo available in the target environment, an agent can usually auto-complete:

- config scaffold generation (`bootstrap-nonui` / `init`)
- path auto-detection for common non-UI layouts (`src`, `source`, `lib`, `cjpm.toml`)
- validation and loop execution commands

Still requires project-specific human-provided info:

- real build command (`verify_command`) when project tooling is custom
- external secrets (`CONTEXT7_API_KEY`, LLM API key)
- network/runtime prerequisites not inferable from repo content

### 4.2 Context7 MCP configuration example

Use the provided sample config:

`configs/project.nonui.context7.sample.toml`

Key fields (URL mode, aligned with Cursor MCP config):

- `knowledge_provider = "mcp"`
- `mcp_server_url = "https://mcp.context7.com/mcp"`
- `mcp_headers = ["CONTEXT7_API_KEY=${CONTEXT7_API_KEY}"]`
- `mcp_tool_name = "query-docs"`

Before running, export your API key:

```bash
export CONTEXT7_API_KEY="<your-context7-api-key>"
```

### 4.3 Multi-model routing and weekly report

Enable multi-model routing in project config:

- `repair_strategy = "multi_llm"`
- `llm_model = "<primary-model>"`
- `llm_model_secondary = "<secondary-model>"`
- `llm_route_rule = "error_type_or_complexity"`
- `llm_secondary_categories = ["syntax", "generic", "type"]`
- `llm_complexity_threshold = 220`

Generate weekly comparison report:

```bash
python3 -m driver.main weekly-report --runs-dir runs --output docs/weekly_model_report.md --days 7
```

---

## 5. Application scenarios

1. New project bootstrap  
   Use one standard workflow instead of project-specific debugging scripts.

2. Team regression / CI support  
   Generate structured diagnosis records for failed builds for review and tracking.

3. Execution base for LLM repair systems  
   Keep model responsibility as "propose plan", and keep file writes + safety checks in execution layer.

---

## 6. Expected value and evaluation

The goal is not "highest automation". The goal is "workflow-based debugging is more stable and effective than blind debugging."

### 6.1 Expected user experience

Users should feel three concrete improvements:

1. Better failure visibility: each iteration records error, plan, patch, and outcome.
2. Controlled changes: even with LLM integration, files are not changed arbitrarily.
3. Reproducible debugging: same input can be rerun and reviewed by the team.

### 6.2 Evaluation metrics

1. Success rate: ratio of `final_status=success` in sample set.
2. Average iterations: average number of iterations for successful cases.
3. Average duration: total time from start to stop.
4. Safety incidents: out-of-scope edits, bypassing PatchApplier, untraceable changes (target: 0).
5. Migration cost: whether new project onboarding needs framework code changes beyond config (target: near 0).

If these metrics are better than free-form LLM/agent debugging for two continuous weeks, this framework is practically validated and ready for multi-model extension.
