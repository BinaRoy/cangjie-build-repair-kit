from __future__ import annotations

from pathlib import Path

from driver.contracts import ErrorBlock


ERROR_HINTS = ["error", "fatal", "undefined", "failed", "exception"]


def extract_root_cause(log_text: str) -> ErrorBlock:
    lines = [ln.strip() for ln in log_text.splitlines() if ln.strip()]
    for ln in lines:
        low = ln.lower()
        if any(h in low for h in ERROR_HINTS):
            family = classify_family(ln)
            excerpt = collect_excerpt(lines, ln)
            return ErrorBlock(family=family, headline=ln[:300], excerpt=excerpt)
    fallback = "No explicit error line found in verify log."
    return ErrorBlock(family="unknown", headline=fallback, excerpt=fallback)


def classify_family(line: str) -> str:
    low = line.lower()
    if "arkui" in low or "component" in low:
        return "arkui"
    if "link" in low or "undefined" in low:
        return "link"
    if "syntax" in low or "parse" in low:
        return "syntax"
    if "cjpm" in low:
        return "cjpm"
    if "hvigor" in low:
        return "hvigor"
    return "compile"


def collect_excerpt(lines: list[str], pivot: str) -> str:
    try:
        idx = lines.index(pivot)
    except ValueError:
        return pivot
    start = max(0, idx - 2)
    end = min(len(lines), idx + 3)
    return "\n".join(lines[start:end])
