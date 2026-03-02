# Cangjie Core Lookup Rules

## Repos

- `knowledge/external/cangjie_compiler`
- `knowledge/external/cangjie_runtime`
- `knowledge/external/cangjie_docs`

## Precision routing

1. Language syntax, semantics, package rules:
   - First: `cangjie_docs/docs/dev-guide/source_zh_cn/**` or `source_en/**`
   - Then: `cangjie_compiler/src/**` for implementation behavior.

2. Compile/build flags, `cjc/cjpm`, cross compilation:
   - First: `cangjie_docs/docs/dev-guide/source_*/compile_and_build/**`
   - Then: `cangjie_compiler/doc/Standalone_Build_Guide*.md`
   - Finally: `cangjie_compiler/src/**` and `cangjie_compiler/integration_build/**`.

3. Runtime crash, missing symbols, stdlib/runtime behavior:
   - First: `cangjie_runtime/README*.md`
   - Runtime build/deploy: `cangjie_runtime/runtime/build_runtime*.md`
   - Stdlib APIs: `cangjie_runtime/stdlib/doc/libs/**`
   - Deep behavior: `cangjie_runtime/runtime/**` and `cangjie_runtime/stdlib/**`.

4. FFI/interoperability:
   - First: `cangjie_docs/docs/dev-guide/source_*/FFI/**`
   - Then: related modules in `cangjie_runtime/stdlib/doc/libs/**`.

5. Macro/generic/advanced type system:
   - First: `cangjie_docs/docs/dev-guide/source_*/Macro/**` and `source_*/generic/**`
   - Then: compiler source for diagnostics mapping in `cangjie_compiler/src/**`.

## Search commands

- Syntax keyword:
  - `rg -n "<keyword>" knowledge/external/cangjie_docs/docs/dev-guide/source_zh_cn`
- Build option / cjpm:
  - `rg -n "cjpm|cjc|compile|build|cross|target" knowledge/external/cangjie_docs/docs/dev-guide/source_*`
- Runtime exception / stdlib API:
  - `rg -n "<exception_or_api>" knowledge/external/cangjie_runtime/stdlib/doc/libs`
- Compiler diagnostic origin:
  - `rg -n "<error_token>" knowledge/external/cangjie_compiler/src`

## Evidence rule

- Every suggested fix must reference at least one existing local file path from the above repos.
- If no path is found, stop and report `insufficient_knowledge_evidence` instead of guessing.
