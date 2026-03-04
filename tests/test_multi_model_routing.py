from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, KnowledgeItem, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
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


class MultiModelRoutingTests(unittest.TestCase):
    def test_routes_to_secondary_by_error_category(self) -> None:
        strategy = MultiModelLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model_primary="model-a",
            model_secondary="model-b",
            route_rule="error_type_or_complexity",
            secondary_categories=["syntax", "generic"],
            complexity_threshold=200,
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
        error = ErrorSchema(
            category="syntax",
            file="src/main.cj",
            line=1,
            message="syntax error",
            context="ctx",
            fingerprint="fp",
        )
        strategy.propose(error, {"knowledge_hits": [], "iteration": 1, "run_id": "r", "project_name": "p"})
        decision = strategy.get_last_route_decision()
        self.assertEqual(decision.get("selected_model_key"), "secondary")
        self.assertEqual(decision.get("selected_model"), "model-b")

    def test_routes_to_secondary_by_complexity_threshold(self) -> None:
        strategy = MultiModelLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model_primary="model-a",
            model_secondary="model-b",
            route_rule="error_type_or_complexity",
            secondary_categories=["syntax"],
            complexity_threshold=40,
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
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="x" * 30,
            context="y" * 30,
            fingerprint="fp",
        )
        strategy.propose(
            error,
            {
                "knowledge_hits": [KnowledgeItem(source="k.md", title="k", content="hint")],
                "iteration": 1,
                "run_id": "r",
                "project_name": "p",
            },
        )
        decision = strategy.get_last_route_decision()
        self.assertEqual(decision.get("selected_model_key"), "secondary")
        self.assertEqual(decision.get("reason"), "complexity")

    def test_run_loop_writes_model_route_decision_into_iteration_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="g3",
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

            run_loop(
                base_dir=base_dir,
                run_id="g3-run",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="syntax",
                    file="src/main.cj",
                    line=1,
                    message="syntax error",
                    context="ctx",
                    fingerprint="fp-g3",
                ),
                strategy=strategy,
                applier=lambda *_args, **_kwargs: PatchResult(
                    applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                ),
                verifier=lambda *_args, **_kwargs: (True, "ok"),
            )

            payload = json.loads((base_dir / "runs" / "g3-run" / "iter_1.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["model_route_decision"]["selected_model_key"], "secondary")
            self.assertEqual(payload["model_route_decision"]["selected_model"], "model-b")


if __name__ == "__main__":
    unittest.main()
