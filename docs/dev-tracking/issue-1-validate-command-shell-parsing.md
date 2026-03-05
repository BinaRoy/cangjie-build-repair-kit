# Issue #1 Development Tracking

- Issue: https://github.com/BinaRoy/cangjie-build-repair-kit/issues/1
- Branch: `issue/1-validate-mis-parses-shell-commands-and-rejects-valid-verify-command-cd-bash-lc`

## Scope

Fix `driver.main validate` command extraction so shell-style commands do not produce false "command not found" errors for shell builtins/flags.

## Implementation Notes

- Updated `_extract_required_commands` in `driver/main.py`:
  - switched to `shlex.split(..., posix=True)` for normalized shell token parsing.
  - added shell wrapper handling for combined bash flags such as `-lc`.
  - added simple shell-chain parsing for `&&`, `||`, `;`, `|` separators.
  - ignored common shell builtins at command head (e.g., `cd`) so only external executables are validated.
  - deduplicated extracted command candidates while preserving order.
- Added tests in `tests/test_validate_command.py`:
  - `test_extract_required_commands_for_shell_chain`
  - `test_extract_required_commands_for_bash_lc_wrapper`
  - `test_validate_command_accepts_shell_style_verify_command`

## Verification Evidence

- `python3 -m unittest tests.test_validate_command -v`
  - Result: PASS (10 tests)
