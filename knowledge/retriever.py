from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from driver.contracts import ErrorBlock, KnowledgeItem


def retrieve_local_knowledge(base_dir: Path, error: ErrorBlock) -> list[KnowledgeItem]:
    hits: list[KnowledgeItem] = []
    patterns = _load_error_patterns(base_dir / "knowledge" / "error_patterns.yaml")
    content = (error.headline + "\n" + error.excerpt).lower()

    for item in patterns:
        keys = [k.lower() for k in item.get("keywords", [])]
        if keys and any(k in content for k in keys):
            hits.append(
                KnowledgeItem(
                    source="knowledge/error_patterns.yaml",
                    title=item.get("id", "pattern"),
                    content=item.get("guidance", ""),
                )
            )

    for doc_name in ["cangjie_recipes.md", "project_conventions.md"]:
        doc_path = base_dir / "knowledge" / doc_name
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        snippet = _find_snippet(text, error.family)
        if snippet:
            hits.append(KnowledgeItem(source=f"knowledge/{doc_name}", title=doc_name, content=snippet))

    hits.extend(_retrieve_from_external_toolchain(base_dir, error))
    hits.extend(_retrieve_from_external_core(base_dir, error))

    # Deduplicate by source+title while preserving order.
    uniq: list[KnowledgeItem] = []
    seen: set[tuple[str, str]] = set()
    for h in hits:
        key = (h.source, h.title)
        if key in seen:
            continue
        uniq.append(h)
        seen.add(key)
    return uniq[:12]


def retrieve_knowledge(base_dir: Path, error: ErrorBlock) -> list[KnowledgeItem]:
    # Backward-compatible entrypoint used by older call sites/tests.
    return retrieve_local_knowledge(base_dir, error)


def _retrieve_from_external_toolchain(base_dir: Path, error: ErrorBlock) -> list[KnowledgeItem]:
    root = base_dir / "knowledge" / "external" / "cangjie_tools"
    if not root.exists():
        return []

    hits: list[KnowledgeItem] = []
    content = f"{error.headline}\n{error.excerpt}".lower()
    tool = _select_tool(content, error.family)
    token = _extract_best_token(content)

    rules = base_dir / "knowledge" / "cangjie" / "toolchain" / "cangjie_tools_lookup_rules.md"
    if rules.exists():
        text = rules.read_text(encoding="utf-8", errors="replace")
        snippet = _find_snippet(text, tool) or _find_snippet(text, "Problem-type to path map")
        if snippet:
            hits.append(
                KnowledgeItem(
                    source="knowledge/cangjie/toolchain/cangjie_tools_lookup_rules.md",
                    title="cangjie_tools_lookup_rules",
                    content=snippet,
                )
            )

    for path in _tool_doc_candidates(root, tool):
        hit = _build_hit(base_dir, path, token)
        if hit:
            hits.append(hit)
        if len(hits) >= 5:
            break
    return hits


def _retrieve_from_external_core(base_dir: Path, error: ErrorBlock) -> list[KnowledgeItem]:
    ext = base_dir / "knowledge" / "external"
    compiler = ext / "cangjie_compiler"
    runtime = ext / "cangjie_runtime"
    docs = ext / "cangjie_docs"
    if not (compiler.exists() and runtime.exists() and docs.exists()):
        return []

    content = f"{error.headline}\n{error.excerpt}".lower()
    token = _extract_best_token(content)
    routes = _core_routes(compiler, runtime, docs, content)

    hits: list[KnowledgeItem] = []
    rules = base_dir / "knowledge" / "cangjie" / "toolchain" / "cangjie_core_lookup_rules.md"
    if rules.exists():
        text = rules.read_text(encoding="utf-8", errors="replace")
        snippet = _find_snippet(text, routes["topic"]) or _find_snippet(text, "Precision routing")
        if snippet:
            hits.append(
                KnowledgeItem(
                    source="knowledge/cangjie/toolchain/cangjie_core_lookup_rules.md",
                    title="cangjie_core_lookup_rules",
                    content=snippet,
                )
            )

    for path in routes["files"]:
        hit = _build_hit(base_dir, path, token)
        if hit:
            hits.append(hit)
        if len(hits) >= 6:
            break
    return hits


def _core_routes(compiler: Path, runtime: Path, docs: Path, content: str) -> dict[str, Any]:
    # Keep routing narrow to improve precision and avoid broad guessing.
    if any(k in content for k in ["runtime", "stack", "panic", "exception", "segmentation", "dll", "symbol"]):
        return {
            "topic": "runtime",
            "files": [
                runtime / "README.md",
                runtime / "runtime" / "build_runtime.md",
                runtime / "runtime" / "build_runtime_zh.md",
                runtime / "stdlib" / "doc" / "libs" / "std" / "core" / "core_package_overview.md",
                docs / "docs" / "dev-guide" / "source_zh_cn" / "Appendix" / "runtime_env.md",
            ],
        }
    if any(k in content for k in ["syntax", "parse", "keyword", "type", "generic", "macro"]):
        return {
            "topic": "syntax",
            "files": [
                docs / "docs" / "dev-guide" / "source_zh_cn" / "basic_programming_concepts" / "program_structure.md",
                docs / "docs" / "dev-guide" / "source_zh_cn" / "function" / "define_functions.md",
                docs / "docs" / "dev-guide" / "source_zh_cn" / "generic" / "generic_overview.md",
                docs / "docs" / "dev-guide" / "source_zh_cn" / "Macro" / "macro_introduction.md",
                compiler / "README.md",
            ],
        }
    # default: compile/build/cjpm/cjc pipeline
    return {
        "topic": "compile_and_build",
        "files": [
            docs / "docs" / "dev-guide" / "source_zh_cn" / "compile_and_build" / "cjpm_usage.md",
            docs / "docs" / "dev-guide" / "source_zh_cn" / "compile_and_build" / "cjc_usage.md",
            docs / "docs" / "dev-guide" / "source_zh_cn" / "compile_and_build" / "cross_compilation.md",
            compiler / "doc" / "Standalone_Build_Guide.md",
            compiler / "README.md",
        ],
    }


def _build_hit(base_dir: Path, path: Path, token: str) -> KnowledgeItem | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    snippet = _find_snippet(text, token) if token else ""
    if not snippet:
        snippet = _find_snippet(text, "error") or _find_snippet(text, "build") or text[:240]
    rel = path.relative_to(base_dir).as_posix()
    return KnowledgeItem(source=rel, title=path.name, content=snippet.strip())


def _select_tool(content: str, family: str) -> str:
    if "cjpm" in content or "compilecangjie" in content or family == "hvigor":
        return "cjpm"
    if "lint" in content or "cjlint" in content:
        return "cjlint"
    if "format" in content or "cjfmt" in content:
        return "cjfmt"
    if "language server" in content or "lsp" in content:
        return "cangjie-language-server"
    if "hyperlang" in content or "arkts" in content or "bridge" in content:
        return "hyperlangExtension"
    if "trace" in content:
        return "cjtrace-recover"
    if "cover" in content:
        return "cjcov"
    return "cjpm"


def _tool_doc_candidates(root: Path, tool: str) -> list[Path]:
    return [
        root / "README.md",
        root / tool / "doc" / "user_guide.md",
        root / tool / "doc" / "user_guide_zh.md",
        root / tool / "doc" / "developer_guide.md",
        root / tool / "doc" / "developer_guide_zh.md",
    ]


def _extract_best_token(content: str) -> str:
    m = re.search(r"exit code\s+(-?\d+)", content)
    if m:
        return m.group(1)
    for t in ("compilecangjie", "cjpm", "cjc", "runtime", "syntax", "build", "error", "failed"):
        if t in content:
            return t
    return ""


def _find_snippet(text: str, token: str) -> str:
    lower = text.lower()
    idx = lower.find(token.lower())
    if idx < 0:
        return ""
    start = max(0, idx - 120)
    end = min(len(text), idx + 260)
    return text[start:end].strip()


def _load_error_patterns(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        pass

    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for ln in raw.splitlines():
        line = ln.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                items.append(current)
            current = {}
            line = line[2:].strip()
            if ":" in line:
                k, v = line.split(":", 1)
                current[k.strip()] = v.strip().strip('"')
            continue
        if current is None:
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            val = v.strip()
            if val.startswith("[") and val.endswith("]"):
                vals = [x.strip().strip('"') for x in val[1:-1].split(",") if x.strip()]
                current[key] = vals
            else:
                current[key] = val.strip('"')
    if current:
        items.append(current)
    return items
