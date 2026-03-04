from __future__ import annotations

from typing import Any

from driver.contracts import PatchAction


ALLOWED_TOP_LEVEL_KEYS = {"can_apply", "rationale", "diff_summary", "actions"}
ALLOWED_ACTION_KEYS = {"file_path", "action", "search", "replace"}


def validate_llm_patch_plan_payload(data: Any) -> tuple[bool, str, dict[str, Any] | None]:
    if not isinstance(data, dict):
        return False, "invalid_patch_plan:not_object", None
    keys = set(data.keys())
    if keys != ALLOWED_TOP_LEVEL_KEYS:
        extra = sorted(keys.difference(ALLOWED_TOP_LEVEL_KEYS))
        missing = sorted(ALLOWED_TOP_LEVEL_KEYS.difference(keys))
        return False, f"invalid_patch_plan:top_level_keys extra={extra} missing={missing}", None

    if not isinstance(data.get("can_apply"), bool):
        return False, "invalid_patch_plan:can_apply_not_bool", None
    if not isinstance(data.get("rationale"), str):
        return False, "invalid_patch_plan:rationale_not_str", None
    if not isinstance(data.get("diff_summary"), str):
        return False, "invalid_patch_plan:diff_summary_not_str", None
    actions_raw = data.get("actions")
    if not isinstance(actions_raw, list):
        return False, "invalid_patch_plan:actions_not_list", None

    actions: list[PatchAction] = []
    for idx, item in enumerate(actions_raw):
        if not isinstance(item, dict):
            return False, f"invalid_patch_plan:action_{idx}_not_object", None
        action_keys = set(item.keys())
        if action_keys != ALLOWED_ACTION_KEYS:
            extra = sorted(action_keys.difference(ALLOWED_ACTION_KEYS))
            missing = sorted(ALLOWED_ACTION_KEYS.difference(action_keys))
            return False, f"invalid_patch_plan:action_{idx}_keys extra={extra} missing={missing}", None
        if not all(isinstance(item.get(k), str) for k in ALLOWED_ACTION_KEYS):
            return False, f"invalid_patch_plan:action_{idx}_field_not_str", None
        actions.append(
            PatchAction(
                file_path=item["file_path"],
                action=item["action"],
                search=item["search"],
                replace=item["replace"],
            )
        )

    normalized = {
        "can_apply": bool(data["can_apply"]),
        "rationale": str(data["rationale"]),
        "diff_summary": str(data["diff_summary"]),
        "actions": actions,
    }
    return True, "ok", normalized
