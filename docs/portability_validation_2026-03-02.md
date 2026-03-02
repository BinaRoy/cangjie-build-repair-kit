# Portability Validation (2026-03-02)

## Scope
- UI project: existing DevEco Cangjie app (`Helloworld`).
- Non-UI project: `examples/nonui_hello`.

## Driver runs
- UI config: `configs/project.helloworld.toml`
  - run_id: `20260302_163044_418_07560a`
  - result: `success` (`verify_passed`)
- Non-UI config: `configs/project.nonui.sample.toml`
  - run_id: `20260302_163123_026_b85c06`
  - result: `success` (`verify_passed`)

## Acceptance mapping
- UI success criterion: build passes and HAP generation passes.
- Non-UI success criterion: `cjpm build` passes.

## Notes
- Added `examples/nonui_hello/run_verify.cmd` to inject required Cangjie runtime/toolchain PATH on Windows.
- Updated run id generation to millisecond + random suffix to avoid collision under concurrent runs.
