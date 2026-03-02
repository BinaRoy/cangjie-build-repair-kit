# cangjie_tools Lookup Rules

## Repo location

- External toolchain repo is placed at:
  `knowledge/external/cangjie_tools`

## First-stop rule

1. Start from `knowledge/external/cangjie_tools/README.md` to identify which tool owns the problem.
2. Enter that tool's `doc/` first (`user_guide*`, then `developer_guide*`).
3. If docs are not enough, go to `src/` for implementation behavior and `config/` for rule/config details.
4. For build/packaging problems, check `build/` next.

## Problem-type to path map

- Project init/dependency/build (`cjpm`):
  - `cjpm/doc/user_guide.md`
  - `cjpm/doc/developer_guide.md`
  - `cjpm/src/`
  - `cjpm/build/`

- Formatter behavior/style output (`cjfmt`):
  - `cjfmt/doc/user_guide.md`
  - `cjfmt/doc/developer_guide.md`
  - `cjfmt/config/`
  - `cjfmt/src/`

- Static analysis/lint rule findings (`cjlint`):
  - `cjlint/doc/user_guide_zh.md`
  - `cjlint/doc/developer_guide_zh.md`
  - `cjlint/config/cjlint_rule_list.json`
  - `cjlint/config/*.json`
  - `cjlint/src/`

- IDE completion/hover/diagnostics/symbol issues (`lsp`):
  - `cangjie-language-server/doc/user_guide*.md`
  - `cangjie-language-server/doc/developer_guide*.md`
  - `cangjie-language-server/src/languageserver/`
  - `cangjie-language-server/test/`

- Multilanguage bridge / ArkTS interop (`hle`):
  - `hyperlangExtension/doc/user_guide*.md`
  - `hyperlangExtension/doc/developer_guide*.md`
  - `hyperlangExtension/src/tool/`
  - `hyperlangExtension/tests/`

- Coverage and report generation (`cjcov`):
  - `cjcov/doc/user_guide_zh.md`
  - `cjcov/doc/developer_guide_zh.md`
  - `cjcov/src/`

- Obfuscated stack trace restore (`cjtrace-recover`):
  - `cjtrace-recover/doc/user_guide_zh.md`
  - `cjtrace-recover/doc/developer_guide_zh.md`
  - `cjtrace-recover/src/`

- Third-party dependency behavior:
  - `third_party/README.md`
  - `third_party/**`

## Fast grep rules (recommended)

- Command/CLI option lookup:
  - `rg -n "subcommand|option|--|参数|命令" knowledge/external/cangjie_tools/<tool>/doc`
- Error message ownership:
  - `rg -n "ERROR|error|failed|失败|诊断" knowledge/external/cangjie_tools/<tool>/src`
- Rule id lookup (cjlint):
  - `rg -n "G_|P_|rule|规则" knowledge/external/cangjie_tools/cjlint/config`
- LSP feature lookup:
  - `rg -n "hover|completion|diagnostic|definition|reference" knowledge/external/cangjie_tools/cangjie-language-server/src`
- Bridge generation lookup:
  - `rg -n "generate|trans_|ark|callback|business" knowledge/external/cangjie_tools/hyperlangExtension/src/tool`

## Escalation rule

- If tool docs and src still cannot explain behavior, follow links from top-level `README.md` to:
  - `cangjie_compiler`
  - `cangjie_docs`
  - `cangjie_build`
  - `cangjie_stdx`
  because many root causes are compiler/SDK side rather than toolchain wrapper side.
