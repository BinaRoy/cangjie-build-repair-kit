# Issue #4 Development Tracking

- Issue: https://github.com/BinaRoy/cangjie-build-repair-kit/issues/4
- Branch: `issue/4-mvp-safe-mode-returns-can-apply-false-for-compile-syntax-error-no-auto-fix-path`

## Scope

Resolve confusion around `can_apply=false` for generic syntax/compile failures in MVP safe mode by explicitly documenting diagnosis-only behavior and actionable configuration to enable repairing strategies.

## Implementation Notes

- Updated fallback rationale in `repair/strategies/rule_based.py` to explicitly state:
  - diagnosis-only safe mode behavior
  - detected family / knowledge hints
  - how to enable auto-repair (`repair_strategy` + `allow_apply_patch`)
- Updated fallback `diff_summary` wording to match diagnosis-only safe mode.
- Added guide doc `docs/mvp_safe_mode_and_repairing.md`:
  - current safe-mode behavior
  - why `stop_no_patch_applied` happens
  - exact config path for enabling stronger auto-repair strategies
- Added README pointer to new guide.
- Added test assertion in `tests/test_rule_based_strategy.py` to enforce rationale includes diagnosis-only and `repair_strategy` guidance.

## Verification Evidence

- `python3 -m unittest tests.test_rule_based_strategy -v`
  - Result: PASS (2 tests)
- `python3 -m unittest discover -s tests -q`
  - Result: PASS (84 tests)
