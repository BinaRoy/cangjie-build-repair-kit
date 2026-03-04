from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PatchResult, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.patcher import apply_patch_plan
from repair.strategies.real_llm import RealLLMStrategy


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


class RealLLMStrategyTests(unittest.TestCase):
    def test_real_llm_strategy_parses_provider_json_output(self) -> None:
        def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"can_apply": true, "rationale": "r", "diff_summary": "d", '
                                '"actions": [{"file_path":"src/main.cj","action":"replace_once",'
                                '"search":"MainAbility()","replace":"EntryAbility()"}]}'
                            )
                        }
                    }
                ]
            }

        strategy = RealLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model="demo-model",
            transport=fake_transport,
        )
        error = ErrorSchema(
            category="link",
            file="src/main.cj",
            line=1,
            message="undefined symbol MainAbility",
            context="ctx",
            fingerprint="fp",
        )

        plan = strategy.propose(error, {"knowledge_hits": [], "iteration": 1, "run_id": "r", "project_name": "p"})

        self.assertTrue(plan.can_apply)
        self.assertEqual(plan.actions[0].replace, "EntryAbility()")

    def test_loop_can_use_real_llm_strategy_without_bypassing_applier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("MainAbility()\n", encoding="utf-8")

            project = ProjectConfig(
                project_name="demo",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=True,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
                require_verify_pass_after_patch=False,
            )

            def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"can_apply": true, "rationale": "r", "diff_summary": "d", '
                                    '"actions": [{"file_path":"src/main.cj","action":"replace_once",'
                                    '"search":"MainAbility()","replace":"EntryAbility()"}]}'
                                )
                            }
                        }
                    ]
                }

            strategy = RealLLMStrategy(
                api_url="https://example.invalid/v1/chat/completions",
                api_key="k",
                model="demo-model",
                transport=fake_transport,
            )

            calls = {"applier": 0}

            def applier_spy(*args, **kwargs) -> PatchResult:
                calls["applier"] += 1
                return apply_patch_plan(*args, **kwargs)

            run_loop(
                base_dir=base_dir,
                run_id="f1-real",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="link",
                    file="src/main.cj",
                    line=1,
                    message="undefined symbol MainAbility",
                    context="ctx",
                    fingerprint="fp",
                ),
                strategy=strategy,
                applier=applier_spy,
            )

            self.assertEqual(calls["applier"], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "EntryAbility()\n")

    def test_real_llm_request_includes_error_knowledge_sources_and_similar_cases(self) -> None:
        captured_payload: dict = {}

        def fake_transport(_url: str, _headers: dict[str, str], payload: dict, _timeout: int) -> dict:
            captured_payload.update(payload)
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"can_apply": false, "rationale": "ok", "diff_summary": "none", "actions": []}'
                        }
                    }
                ]
            }

        strategy = RealLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model="demo-model",
            transport=fake_transport,
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=7,
            message="compile failed",
            context="ctx",
            fingerprint="fp-f2",
        )
        strategy.propose(
            error,
            {
                "knowledge_hits": [],
                "knowledge_sources": ["knowledge/error_patterns.yaml"],
                "similar_cases": [{"case_id": "case-1", "fingerprint": "fp-x", "score": 1.0}],
                "iteration": 1,
                "run_id": "run-f2",
                "project_name": "demo",
            },
        )

        self.assertIn("messages", captured_payload)
        user_content = captured_payload["messages"][1]["content"]
        request_obj = __import__("json").loads(user_content)
        self.assertIn("error", request_obj)
        self.assertIn("knowledge_sources", request_obj)
        self.assertIn("similar_cases", request_obj)

    def test_real_llm_rejects_plan_with_unknown_top_level_fields(self) -> None:
        def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"can_apply": true, "rationale": "r", "diff_summary": "d", '
                                '"actions": [], "unexpected": "x"}'
                            )
                        }
                    }
                ]
            }

        strategy = RealLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model="demo-model",
            transport=fake_transport,
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=7,
            message="compile failed",
            context="ctx",
            fingerprint="fp-f3-a",
        )

        plan = strategy.propose(error, {"knowledge_hits": [], "iteration": 1, "run_id": "r", "project_name": "p"})

        self.assertFalse(plan.can_apply)
        self.assertIn("invalid", plan.rationale.lower())

    def test_real_llm_rejects_plan_with_invalid_action_shape(self) -> None:
        def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"can_apply": true, "rationale": "r", "diff_summary": "d", '
                                '"actions": [{"file_path":"src/main.cj","action":"replace_once","bad":"x"}]}'
                            )
                        }
                    }
                ]
            }

        strategy = RealLLMStrategy(
            api_url="https://example.invalid/v1/chat/completions",
            api_key="k",
            model="demo-model",
            transport=fake_transport,
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=7,
            message="compile failed",
            context="ctx",
            fingerprint="fp-f3-b",
        )

        plan = strategy.propose(error, {"knowledge_hits": [], "iteration": 1, "run_id": "r", "project_name": "p"})

        self.assertFalse(plan.can_apply)
        self.assertIn("invalid", plan.rationale.lower())


if __name__ == "__main__":
    unittest.main()
