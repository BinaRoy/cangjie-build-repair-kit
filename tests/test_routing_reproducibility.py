from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.strategies.multi_llm import MultiModelLLMStrategy


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="compile failed",
            artifact_checks={},
        )


class RoutingReproducibilityTests(unittest.TestCase):
    def test_same_input_produces_same_model_route_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="g4",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                repair_strategy="multi_llm",
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
            )
            parser = lambda _text: ErrorSchema(  # noqa: E731
                category="syntax",
                file="src/main.cj",
                line=1,
                message="syntax error",
                context="ctx",
                fingerprint="fp-g4",
            )
            strategy = MultiModelLLMStrategy(
                api_url="https://example.invalid/v1/chat/completions",
                api_key="k",
                model_primary="model-a",
                model_secondary="model-b",
                route_rule="error_type_or_complexity",
                secondary_categories=["syntax"],
                complexity_threshold=9999,
                transport=lambda *_args, **_kwargs: {
                    "choices": [
                        {
                            "message": {
                                "content": '{"can_apply": false, "rationale": "r", "diff_summary": "d", "actions": []}'
                            }
                        }
                    ]
                },
            )

            for run_id in ("g4-run-1", "g4-run-2"):
                run_loop(
                    base_dir=base_dir,
                    run_id=run_id,
                    project=project,
                    policy=policy,
                    adapter=_FailingAdapter(),
                    parser=parser,
                    strategy=strategy,
                    applier=lambda *_args, **_kwargs: PatchResult(
                        applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                    ),
                    verifier=lambda *_args, **_kwargs: (True, "ok"),
                )

            iter1 = json.loads((base_dir / "runs" / "g4-run-1" / "iter_1.json").read_text(encoding="utf-8"))
            iter2 = json.loads((base_dir / "runs" / "g4-run-2" / "iter_1.json").read_text(encoding="utf-8"))
            self.assertEqual(iter1["model_route_decision"], iter2["model_route_decision"])


if __name__ == "__main__":
    unittest.main()
