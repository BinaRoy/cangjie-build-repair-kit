from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, base_dir: Path, run_id: str) -> None:
        self.run_dir = (base_dir / run_id).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def write_verify_log(self, iteration: int, text: str, phase: str = "pre") -> Path:
        suffix = "" if phase == "pre" else f"_{phase}"
        path = self.run_dir / f"verify_iter_{iteration}{suffix}.log"
        path.write_text(text, encoding="utf-8")
        return path

    def write_iteration(self, iteration: int, payload: dict[str, Any]) -> Path:
        path = self.run_dir / f"iter_{iteration}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_summary(self, payload: dict[str, Any]) -> Path:
        path = self.run_dir / "summary.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path 

    def write_preflight(self, payload: dict[str, Any]) -> Path:
        path = self.run_dir / "preflight.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_error(self, iteration: int, payload: dict[str, Any]) -> Path:
        path = self.run_dir / f"error_iter_{iteration}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_patch_plan(self, iteration: int, payload: dict[str, Any]) -> Path:
        path = self.run_dir / f"patch_plan_iter_{iteration}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_patch_diff(self, iteration: int, diff_text: str) -> Path:
        path = self.run_dir / f"patch_iter_{iteration}.diff"
        path.write_text(diff_text, encoding="utf-8")
        return path
