# Issue #9 Development Tracking

- Issue: https://github.com/BinaRoy/cangjie-build-repair-kit/issues/9
- Branch: `issue/9-rule-based-diagnosis-mode-detects-compile-errors-but-provides-no-actionable-manual-fix-guidance`

## Scope

Provide actionable manual-fix guidance in rule-based diagnosis mode when no automatic patch is generated.

## Implementation Notes

- Updated `repair/strategies/rule_based.py`:
  - Added `_build_manual_fix_guidance(error)` helper.
  - Included manual fix guidance in fallback rationale when `can_apply=false`.
  - Guidance now includes probable location (`file:line` when available) and concrete next steps (inspect syntax region, apply minimal fix, rerun build).
- Updated test `tests/test_rule_based_strategy.py`:
  - Ensures fallback rationale contains file/line location and "manual fix" wording.

## Verification Evidence

- `python3 -m unittest tests.test_rule_based_strategy -v` PASS
- `python3 -m unittest discover -s tests -q` PASS (84 tests)
