# Issue #2 Development Tracking

- Issue: https://github.com/BinaRoy/cangjie-build-repair-kit/issues/2
- Branch: `issue/2-bootstrap-nonui-path-auto-detection-fails-on-monorepo-root-and-creates-invalid-editable-paths`

## Scope

Fix `bootstrap-nonui` so monorepo roots with nested Cangjie modules generate a valid module-specific workdir/editable paths configuration.

## Implementation Notes

- Added `_detect_non_ui_module_roots(root)` in `driver/main.py` to recursively locate `cjpm.toml` module roots.
- Updated `_bootstrap_non_ui` to:
  - choose a module root automatically (nearest depth, then lexical order)
  - set generated `workdir` to the selected module root
  - detect `editable_paths` relative to selected module root
  - avoid forcing `<fill_verify_command>` when selected module already has `cjpm.toml`
  - append a warning block in `FOLLOW_GUIDE.md` when multiple module candidates are detected
- Added regression tests in `tests/test_bootstrap_nonui.py`:
  - `test_bootstrap_nonui_selects_nested_module_workdir`
  - `test_bootstrap_nonui_warns_when_multiple_modules_detected`

## Verification Evidence

- `python3 -m unittest tests.test_bootstrap_nonui -v`
  - Result: PASS (4 tests)
- `python3 -m unittest discover -s tests -q`
  - Result: PASS (83 tests)
