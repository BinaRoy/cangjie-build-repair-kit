from __future__ import annotations

import hashlib
import re

from driver.contracts import ErrorSchema


ERROR_HINTS = ["error", "fatal", "undefined", "failed", "exception"]
FILE_LINE_RE = re.compile(r"(?P<file>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+):(?P<line>\d+)(?::\d+)?")


def extract_root_cause(log_text: str) -> ErrorSchema:
    lines = [ln.strip() for ln in log_text.splitlines() if ln.strip()]
    for ln in lines:
        low = ln.lower()
        if any(h in low for h in ERROR_HINTS):
            category = classify_family(ln)
            file_path, line_no = parse_file_and_line(ln)
            excerpt = collect_excerpt(lines, ln)
            message = ln[:300]
            return ErrorSchema(
                category=category,
                file=file_path,
                line=line_no,
                message=message,
                context=excerpt,
                fingerprint=build_fingerprint(category, file_path, line_no, message),
            )
    fallback = "No explicit error line found in verify log."
    return ErrorSchema(
        category="unknown",
        file="",
        line=None,
        message=fallback,
        context=fallback,
        fingerprint=build_fingerprint("unknown", "", None, fallback),
    )


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


def parse_file_and_line(line: str) -> tuple[str, int | None]:
    matched = FILE_LINE_RE.search(line)
    if not matched:
        return "", None
    file_path = matched.group("file").replace("\\", "/")
    return file_path, int(matched.group("line"))


def build_fingerprint(category: str, file_path: str, line_no: int | None, message: str) -> str:
    normalized_file = file_path.lower().strip()
    normalized_line = str(line_no) if line_no is not None else ""
    normalized_message = message.strip().lower()
    normalized_message = re.sub(r"^\[[^\]]+\]\s*", "", normalized_message)
    normalized_message = re.sub(r"^[a-z0-9_./\\-]+\.[a-z0-9_]+:\d+(?::\d+)?\s*", "", normalized_message)
    normalized_message = re.sub(r"^(error|fatal|exception)\s*:\s*", "", normalized_message)
    normalized_message = re.sub(r"\s+", " ", normalized_message)
    raw = "|".join([category.strip().lower(), normalized_file, normalized_line, normalized_message])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
