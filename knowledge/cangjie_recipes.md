# Cangjie Recipes (Minimal)

## syntax
- Keep package name consistent with `cjpm.toml` package name.
- Prioritize first syntax/parse error before fixing cascaded diagnostics.

## arkui
- `@Entry` + `@Component` class should expose `func build()`.
- Event callback lambda should keep assignment targets valid for `@State` fields.

## ability
- Ability registration string and constructor type must match actual class naming.
