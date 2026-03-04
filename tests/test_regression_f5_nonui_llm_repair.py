from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ErrorSchema, PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop
from repair.strategies.real_llm import RealLLMStrategy


class _FileStateAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        target = Path(project.workdir) / "src" / "main.cj"
        text = target.read_text(encoding="utf-8")
        if "EntryAbility()" in text:
            return VerifyResult(
                success=True,
                exit_code=0,
                duration_sec=0.01,
                command=project.verify_command,
                stdout="build ok",
                stderr="",
                artifact_checks={},
            )
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="src/main.cj:1:1 error: undefined symbol MainAbility",
            artifact_checks={},
        )


class F5NonUIRepairRegressionTests(unittest.TestCase):
    def test_rule_based_fails_but_real_llm_repairs_nonui_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "nonui_sample"
            target = workdir / "src" / "main.cj"
            target.parent.mkdir(parents=True)
            target.write_text("MainAbility()\n", encoding="utf-8")

            parser = lambda _text: ErrorSchema(  # noqa: E731
                category="compile",
                file="src/main.cj",
                line=1,
                message="undefined symbol MainAbility",
                context="ctx",
                fingerprint="fp-f5-nonui",
            )

            rule_project = ProjectConfig(
                project_name="f5-rule",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                repair_strategy="rule_based",
            )
            rule_policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=True,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
                require_verify_pass_after_patch=True,
            )
            rule_summary = run_loop(
                base_dir=base_dir,
                run_id="f5-rule-run",
                project=rule_project,
                policy=rule_policy,
                adapter=_FileStateAdapter(),
                parser=parser,
            )
            self.assertEqual(rule_summary.final_status, "failed")
            self.assertEqual(rule_summary.stop_reason, "stop_no_patch_applied")
            self.assertEqual(target.read_text(encoding="utf-8"), "MainAbility()\n")

            def fake_transport(_url: str, _headers: dict[str, str], _payload: dict, _timeout: int) -> dict:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"can_apply": true, "rationale": "fix main ability", '
                                    '"diff_summary": "replace ability symbol", '
                                    '"actions": [{"file_path":"src/main.cj","action":"replace_once",'
                                    '"search":"MainAbility()","replace":"EntryAbility()"}]}'
                                )
                            }
                        }
                    ]
                }

            llm_project = ProjectConfig(
                project_name="f5-llm",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                repair_strategy="llm",
            )
            llm_policy = PolicyConfig(
                max_iterations=2,
                allow_apply_patch=True,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
                require_verify_pass_after_patch=True,
            )
            llm_summary = run_loop(
                base_dir=base_dir,
                run_id="f5-llm-run",
                project=llm_project,
                policy=llm_policy,
                adapter=_FileStateAdapter(),
                parser=parser,
                strategy=RealLLMStrategy(
                    api_url="https://example.invalid/v1/chat/completions",
                    api_key="k",
                    model="demo-model",
                    transport=fake_transport,
                ),
            )
            self.assertEqual(llm_summary.final_status, "success")
            self.assertEqual(llm_summary.stop_reason, "verify_passed")
            self.assertEqual(target.read_text(encoding="utf-8"), "EntryAbility()\n")


if __name__ == "__main__":
    unittest.main()
