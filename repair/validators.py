from __future__ import annotations

from pathlib import Path

from driver.contracts import PatchResult, PolicyConfig, ProjectConfig


def validate_patch_result(
    patch_result: PatchResult,
    project: ProjectConfig,
    policy: PolicyConfig,
    changed_file_history: set[str],
) -> tuple[bool, str]:
    if not patch_result.applied:
        return True, "No patch applied; gate passed."

    if len(patch_result.changed_files) > policy.max_files_changed_per_iter:
        return False, "Exceeded max_files_changed_per_iter"

    editable = [Path(p).as_posix() for p in project.editable_paths]
    for file_path in patch_result.changed_files:
        fp = Path(file_path).as_posix()
        if not any(fp.startswith(prefix) for prefix in editable):
            return False, f"Changed file outside editable_paths: {file_path}"
        lines = patch_result.changed_lines_per_file.get(file_path, 0)
        if lines > policy.max_changed_lines_per_file:
            return False, f"Changed lines exceeded in {file_path}"
        if lines < policy.min_changed_lines_when_patch_applied:
            return False, f"Changed lines below minimum in {file_path}"

    total = len(changed_file_history.union(set(patch_result.changed_files)))
    if total > policy.max_total_files_changed:
        return False, "Exceeded max_total_files_changed"

    if policy.require_non_scaffold_patch:
        ok, msg = _validate_no_scaffold_markers(project, policy, patch_result.changed_files)
        if not ok:
            return False, msg

    return True, "Patch gate passed."


def _validate_no_scaffold_markers(
    project: ProjectConfig,
    policy: PolicyConfig,
    changed_files: list[str],
) -> tuple[bool, str]:
    workdir = Path(project.workdir).resolve()
    markers = [m.lower() for m in policy.scaffold_markers]
    for rel in changed_files:
        path = (workdir / rel).resolve()
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for marker in markers:
            if marker and marker.lower() in text:
                return False, f"Scaffold marker detected in changed file {rel}: {marker}"
    return True, "No scaffold markers detected."
