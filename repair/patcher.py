from __future__ import annotations

from pathlib import Path

from driver.contracts import PatchPlan, PatchResult, PolicyConfig, ProjectConfig


def apply_patch_plan(plan: PatchPlan, project: ProjectConfig, policy: PolicyConfig) -> PatchResult:
    if not policy.allow_apply_patch:
        return PatchResult(
            applied=False,
            changed_files=[],
            changed_lines_per_file={},
            message="Patch application disabled by policy.allow_apply_patch=false.",
        )
    if not plan.can_apply or not plan.actions:
        return PatchResult(
            applied=False,
            changed_files=[],
            changed_lines_per_file={},
            message="No patch actions to apply.",
        )

    changed_files: list[str] = []
    changed_lines: dict[str, int] = {}
    workdir = Path(project.workdir).resolve()
    editable_roots = [(workdir / p).resolve() for p in project.editable_paths]

    for act in plan.actions:
        if act.action != "replace_once":
            return PatchResult(False, changed_files, changed_lines, f"Unsupported action: {act.action}")
        if not act.search:
            return PatchResult(False, changed_files, changed_lines, "Missing search text for replace_once.")

        target = (workdir / act.file_path).resolve()
        if not target.exists():
            return PatchResult(False, changed_files, changed_lines, f"Target file not found: {act.file_path}")
        if not _is_under_editable_roots(target, editable_roots):
            return PatchResult(False, changed_files, changed_lines, f"Target outside editable_paths: {act.file_path}")

        old = target.read_text(encoding="utf-8", errors="replace")
        if act.search not in old:
            return PatchResult(False, changed_files, changed_lines, f"Search text not found in {act.file_path}")
        new = old.replace(act.search, act.replace, 1)
        if new == old:
            continue

        target.write_text(new, encoding="utf-8")
        rel = target.relative_to(workdir).as_posix()
        changed_files.append(rel)
        changed_lines[rel] = _changed_line_count(old, new)

    if not changed_files:
        return PatchResult(False, [], {}, "No effective file changes were produced.")
    return PatchResult(True, changed_files, changed_lines, "Patch actions applied.")


def _is_under_editable_roots(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _changed_line_count(old: str, new: str) -> int:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    total = max(len(old_lines), len(new_lines))
    changed = 0
    for i in range(total):
        a = old_lines[i] if i < len(old_lines) else ""
        b = new_lines[i] if i < len(new_lines) else ""
        if a != b:
            changed += 1
    return changed
