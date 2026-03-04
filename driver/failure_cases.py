from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher


@dataclass
class FailureCaseRecord:
    case_id: str
    fingerprint: str
    context: dict[str, Any]
    plan: dict[str, Any]
    result: dict[str, Any]
    run_id: str
    iteration: int


def fingerprint_bucket(fingerprint: str) -> str:
    text = (fingerprint or "").strip()
    if not text:
        return "unknown"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def create_failure_case_record(
    *,
    fingerprint: str,
    context: dict[str, Any],
    plan: dict[str, Any],
    result: dict[str, Any],
    run_id: str,
    iteration: int,
) -> FailureCaseRecord:
    bucket = fingerprint_bucket(fingerprint)
    case_id = f"case_{bucket}_{run_id}_{iteration}_{uuid.uuid4().hex[:8]}"
    return FailureCaseRecord(
        case_id=case_id,
        fingerprint=fingerprint,
        context=dict(context),
        plan=dict(plan),
        result=dict(result),
        run_id=run_id,
        iteration=iteration,
    )


class FailureCaseStore:
    def __init__(self, base_dir: Path) -> None:
        self.root = (base_dir / "failure_cases").resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_case(self, record: FailureCaseRecord) -> Path:
        bucket = fingerprint_bucket(record.fingerprint)
        out_dir = self.root / bucket
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{record.case_id}.json"
        path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_case_dedup(self, record: FailureCaseRecord) -> Path:
        existing = self.find_by_fingerprint(record.fingerprint)
        if existing is not None:
            return existing
        return self.write_case(record)

    def find_by_fingerprint(self, fingerprint: str) -> Path | None:
        bucket = fingerprint_bucket(fingerprint)
        bucket_dir = self.root / bucket
        if not bucket_dir.exists():
            return None
        for path in bucket_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(payload.get("fingerprint", "")) == fingerprint:
                return path
        return None

    def find_similar_cases(self, fingerprint: str, top_k: int = 3) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        rows: list[dict[str, Any]] = []
        for path in self.root.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            fp = str(payload.get("fingerprint", "")).strip()
            if not fp:
                continue
            score = self._similarity(fingerprint, fp)
            row = {
                "case_id": str(payload.get("case_id", "")),
                "fingerprint": fp,
                "score": round(score, 6),
                "context": payload.get("context", {}),
                "plan": payload.get("plan", {}),
                "result": payload.get("result", {}),
                "run_id": str(payload.get("run_id", "")),
                "iteration": int(payload.get("iteration", 0)),
            }
            rows.append(row)
        rows.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return rows[:top_k]

    def _similarity(self, left: str, right: str) -> float:
        l = (left or "").strip().lower()
        r = (right or "").strip().lower()
        if not l and not r:
            return 1.0
        if not l or not r:
            return 0.0
        if l == r:
            return 1.0
        return SequenceMatcher(None, l, r).ratio()
