# Cangjie Build-Repair Template (MVP)

This is a minimal, configurable build -> diagnose -> repair-plan -> rebuild workflow.

## What it does now
- Runs project verify command through adapter.
- Extracts root cause from logs.
- Retrieves lightweight Cangjie knowledge snippets.
- Produces structured per-iteration records under `runs/<run_id>/`.
- Enforces policy constraints for future repair steps.
- Supports constrained patch execution (`replace_once`) behind policy flag.
- Can require post-patch verify to pass before continuing.
- Runs preflight checks before loop (toolchain bootstrap and `cjpm --help`).
- Preflight failure writes structured remediation hints to `runs/<run_id>/preflight.json`.
- Enforces knowledge-evidence on failures (must have local source-backed hits).
- Enforces non-scaffold patch policy (blocks placeholder-only changes).

## What it does not do yet
- No LLM call is wired in this MVP.
- No automatic source patch is applied by default.

## Quick start
```powershell
cd d:\DevEvo_Projects\Helloworld\cangjie-repair-template
python -m pip install -e .
cangjie-repair run --project-config configs/project.helloworld.toml --policy-config configs/policy.default.toml
```

Non-UI sample:
```powershell
cangjie-repair run --project-config configs/project.nonui.sample.toml --policy-config configs/policy.default.toml
```

Generate reusable config templates:
```powershell
cangjie-repair init --template ui --output-dir .\my-configs --project-name my-ui --workdir d:\path\to\project
```

Export product bundle (filtered):
```powershell
cangjie-repair export --output-dir .\dist\product_bundle --force
```

Outputs:
- Iteration logs: `runs/<run_id>/iter_*.json`
- Raw verify logs: `runs/<run_id>/verify_iter_*.log`
- Summary: `runs/<run_id>/summary.json`
- Markdown report: `runs/<run_id>/report.md`

## Extension points
- `repair/planner.py`: swap with LLM/multi-agent planner.
- `repair/patcher.py`: apply patch plans with strict path limits.
- `knowledge/retriever.py`: replace local lookup with MCP-backed retrieval.

## Validation
- Portability validation record: `docs/portability_validation_2026-03-02.md`

## Knowledge routing
- Toolchain repo routing: `knowledge/cangjie/toolchain/cangjie_tools_lookup_rules.md`
- Core repos routing (`compiler/runtime/docs`): `knowledge/cangjie/toolchain/cangjie_core_lookup_rules.md`
