# Issue #3 Development Tracking

- Issue: https://github.com/BinaRoy/cangjie-build-repair-kit/issues/3
- Branch: `issue/3-default-policy-blocks-repair-loop-before-planning-when-local-knowledge-hits-are-empty`

## Scope

Avoid premature `stop_no_knowledge_hits` for rule-based syntax/compile failures so the planner can still attempt deterministic repair planning when knowledge hits are empty.

## Implementation Notes

- Updated `driver/loop.py` knowledge gate flow:
  - added `_should_relax_knowledge_hit_gate(active_strategy, error)`.
  - relaxed `min_knowledge_hits` enforcement only when:
    - active strategy is `RuleBasedStrategy`
    - error category is `syntax` or `compile`
- Kept strict gate behavior for non-rule-based strategies (including real LLM path) to preserve safety expectations.
- Added regression test in `tests/test_loop_injection.py`:
  - `test_syntax_error_does_not_stop_on_no_knowledge_hits_for_rule_based`
- Verified existing LLM safety gate test still passes:
  - `test_real_llm_is_not_called_when_knowledge_evidence_missing`

## Verification Evidence

- `python3 -m unittest tests.test_loop_injection tests.test_real_llm_safety -v`
  - Result: PASS (5 tests)
- `python3 -m unittest discover -s tests -q`
  - Result: PASS (84 tests)
