# MVP Safe Mode and Repair-Enabling Guide

## Current behavior

The default rule-based planner keeps a diagnosis-first safe mode for generic failures:

- It can generate deterministic patches for explicit high-confidence patterns already implemented in rules.
- For unmatched compile/syntax/generic failures, it returns `can_apply=false` and records rationale for traceability.

This behavior is intentional in MVP to avoid low-confidence automatic edits.

## Why you may see `stop_no_patch_applied`

If the strategy returns no actionable patch (`can_apply=false`), the loop will stop with:

- `stop_no_patch_applied` when `allow_apply_patch=true`
- `stop_patch_disabled_by_policy` when `allow_apply_patch=false`

## How to enable stronger auto-repair

Use a repair-capable strategy and keep patch application enabled:

1. In project config:
   - set `repair_strategy = "llm"` or `repair_strategy = "multi_llm"`
   - configure model settings (`llm_api_url`, `llm_api_key`, `llm_model`, etc.)
2. In policy config:
   - set `allow_apply_patch = true`
3. Run validation and loop:
   - `python3 -m driver.main validate --project-config <project.toml> --policy-config <policy.toml>`
   - `python3 -m driver.main run --project-config <project.toml> --policy-config <policy.toml>`

## Scope note

If you need deterministic auto-fixes for additional syntax patterns in rule-based mode, add narrowly-scoped pattern rules with tests first, then verify with project test suite.
