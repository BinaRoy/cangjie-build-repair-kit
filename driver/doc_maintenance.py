from __future__ import annotations

from pathlib import Path


def append_update_entry(
    doc_path: Path,
    date_text: str,
    change: str,
    modules: list[str],
    verify_command: str,
    result: str,
    risk: str,
) -> Path:
    text = doc_path.read_text(encoding="utf-8", errors="replace") if doc_path.exists() else ""
    module_text = ", ".join(modules) if modules else "(none)"
    block = "\n".join(
        [
            "",
            f"### Update {date_text}",
            f"- 变更: {change}",
            f"- 影响模块: {module_text}",
            f"- 验证命令: {verify_command}",
            f"- 结果: {result}",
            f"- 风险/待办: {risk}",
        ]
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    return doc_path
