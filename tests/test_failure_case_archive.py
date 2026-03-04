from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchPlan, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="src/main.cj:7:2 error: compile failed",
            artifact_checks={},
        )


class _NoopStrategy:
    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        del error, context
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class FailureCaseArchiveTests(unittest.TestCase):
    def test_run_loop_archives_failure_case_on_failed_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="e2-archive",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
            )

            run_loop(
                base_dir=base_dir,
                run_id="e2-run-1",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=7,
                    message="compile failed",
                    context="ctx",
                    fingerprint="fp-e2",
                ),
                strategy=_NoopStrategy(),
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            case_files = list((base_dir / "failure_cases").rglob("*.json"))
            self.assertEqual(len(case_files), 1)
            payload = json.loads(case_files[0].read_text(encoding="utf-8"))
            self.assertIn("case_id", payload)
            self.assertEqual(payload["fingerprint"], "fp-e2")
            self.assertIn("context", payload)
            self.assertIn("plan", payload)
            self.assertIn("result", payload)

    def test_failure_case_archive_deduplicates_by_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="e2-dedup",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
            )

            parser = lambda _text: ErrorSchema(  # noqa: E731
                category="compile",
                file="src/main.cj",
                line=7,
                message="compile failed",
                context="ctx",
                fingerprint="fp-e2-dedup",
            )

            for run_id in ("e2-run-a", "e2-run-b"):
                run_loop(
                    base_dir=base_dir,
                    run_id=run_id,
                    project=project,
                    policy=policy,
                    adapter=_FailingAdapter(),
                    parser=parser,
                    strategy=_NoopStrategy(),
                    applier=lambda *_args, **_kwargs: PatchResult(
                        applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                    ),
                    verifier=lambda *_args, **_kwargs: (True, "ok"),
                )

            case_files = list((base_dir / "failure_cases").rglob("*.json"))
            self.assertEqual(len(case_files), 1)
            payload = json.loads(case_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["fingerprint"], "fp-e2-dedup")


if __name__ == "__main__":
    unittest.main()
