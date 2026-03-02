from __future__ import annotations

from driver.contracts import ErrorBlock, KnowledgeItem, PatchAction, PatchPlan


def propose_patch_plan(error: ErrorBlock, knowledge_hits: list[KnowledgeItem]) -> PatchPlan:
    hit_titles = ", ".join(item.title for item in knowledge_hits[:2]) if knowledge_hits else "none"

    # Minimal deterministic rule; behavior remains explicit and auditable.
    content = f"{error.headline}\n{error.excerpt}".lower()
    if "undefined" in content and "mainability" in content:
        return PatchPlan(
            can_apply=True,
            rationale="Detected undefined MainAbility symbol in ability registration context.",
            diff_summary="Replace MainAbility() with EntryAbility() in ability registration file.",
            actions=[
                PatchAction(
                    file_path="entry/src/main/cangjie/ability_mainability_entry.cj",
                    action="replace_once",
                    search="MainAbility()",
                    replace="EntryAbility()",
                )
            ],
        )

    rationale = (
        "MVP planner is in safe mode and does not auto-edit files yet. "
        f"Detected family={error.family}, matched knowledge={hit_titles}."
    )
    return PatchPlan(
        can_apply=False,
        rationale=rationale,
        diff_summary="No patch generated in MVP safe mode.",
        actions=[],
    )
