from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.strategies.real_llm import RealLLMStrategy


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


class RealLLMSafetyTests(unittest.TestCase):
    def test_real_llm_is_not_called_when_knowledge_evidence_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)

            calls = {"transport": 0}

            def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
                calls["transport"] += 1
                return {"choices": [{"message": {"content": '{"can_apply": false, "rationale": "r", "diff_summary": "d", "actions": []}'}}]}

            strategy = RealLLMStrategy(
                api_url="https://example.invalid/v1/chat/completions",
                api_key="k",
                model="demo-model",
                transport=fake_transport,
            )
            project = ProjectConfig(
                project_name="f4-no-evidence",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                knowledge_provider="local",
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=True,
                require_preflight=False,
                require_knowledge_lookup_on_failure=True,
                min_knowledge_hits=1,
                require_knowledge_source_evidence=True,
                require_verify_pass_after_patch=False,
            )

            summary = run_loop(
                base_dir=base_dir,
                run_id="f4-no-evidence",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=7,
                    message="compile failed",
                    context="ctx",
                    fingerprint="fp-f4-no-evidence",
                ),
                strategy=strategy,
            )

            self.assertEqual(summary.stop_reason, "stop_no_knowledge_hits")
            self.assertEqual(calls["transport"], 0)

    def test_real_llm_out_of_scope_patch_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("MainAbility()\n", encoding="utf-8")
            outside = workdir / "outside.cj"

            def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"can_apply": true, "rationale": "r", "diff_summary": "d", '
                                    '"actions": [{"file_path":"outside.cj","action":"replace_once",'
                                    '"search":"x","replace":"y"}]}'
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
            project = ProjectConfig(
                project_name="f4-scope",
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

            summary = run_loop(
                base_dir=base_dir,
                run_id="f4-scope",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=7,
                    message="compile failed",
                    context="ctx",
                    fingerprint="fp-f4-scope",
                ),
                strategy=strategy,
            )

            self.assertEqual(summary.stop_reason, "stop_no_patch_applied")
            self.assertFalse(outside.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "MainAbility()\n")

    def test_real_llm_direct_write_is_detected_and_rolled_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("MainAbility()\n", encoding="utf-8")

            def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
                # Simulate malicious provider side-effect write during strategy execution.
                target.write_text("MALICIOUS_WRITE\n", encoding="utf-8")
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"can_apply": false, "rationale": "r", "diff_summary": "d", "actions": []}'
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
            project = ProjectConfig(
                project_name="f4-write",
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

            summary = run_loop(
                base_dir=base_dir,
                run_id="f4-write",
                project=project,
                policy=policy,
                adapter=_FailingAdapter(),
                parser=lambda _text: ErrorSchema(
                    category="compile",
                    file="src/main.cj",
                    line=7,
                    message="compile failed",
                    context="ctx",
                    fingerprint="fp-f4-write",
                ),
                strategy=strategy,
            )

            self.assertEqual(summary.stop_reason, "stop_strategy_direct_write_detected")
            self.assertEqual(target.read_text(encoding="utf-8"), "MainAbility()\n")


if __name__ == "__main__":
    unittest.main()
