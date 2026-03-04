from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.base import BuildAdapter
from driver.contracts import (
    ErrorSchema,
    KnowledgeItem,
    PatchPlan,
    PatchResult,
    PolicyConfig,
    ProjectConfig,
    VerifyResult,
)
from driver.loop import run_loop


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="src/main.cj:10:2 error: compile failed",
            artifact_checks={},
        )


class _NoopStrategy:
    def propose(self, error: ErrorSchema, context: dict[str, object]) -> PatchPlan:
        del error, context
        return PatchPlan(can_apply=False, rationale="stub", diff_summary="stub", actions=[])


class D5KnowledgeRegressionTests(unittest.TestCase):
    def test_mcp_mode_records_mcp_source_and_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            project = ProjectConfig(
                project_name="d5-mcp",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                knowledge_provider="mcp",
                mcp_server_url="https://mcp.context7.com/mcp",
                mcp_headers=["CONTEXT7_API_KEY=test-key"],
                mcp_tool_name="query-docs",
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=False,
            )

            with patch("knowledge.mcp_provider.MCPKnowledgeProvider.retrieve") as retrieve_mock:
                retrieve_mock.return_value = [
                    KnowledgeItem(
                        source="mcp://context7/cangjie/syntax",
                        title="cangjie-syntax",
                        content="tip",
                    )
                ]
                run_loop(
                    base_dir=base_dir,
                    run_id="d5-mcp-ok",
                    project=project,
                    policy=policy,
                    adapter=_FailingAdapter(),
                    strategy=_NoopStrategy(),
                    applier=lambda *_args, **_kwargs: PatchResult(
                        applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                    ),
                    verifier=lambda *_args, **_kwargs: (True, "ok"),
                )

            iter_payload = json.loads((base_dir / "runs" / "d5-mcp-ok" / "iter_1.json").read_text(encoding="utf-8"))
            self.assertIn("mcp://context7/cangjie/syntax", iter_payload["knowledge_sources"])
            self.assertEqual(iter_payload["knowledge_provider_decision"]["provider_name"], "mcp")
            self.assertEqual(iter_payload["knowledge_provider_decision"]["hit_count"], 1)

    def test_hybrid_mode_falls_back_to_local_and_records_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)
            knowledge_dir = base_dir / "knowledge"
            knowledge_dir.mkdir(parents=True)
            (knowledge_dir / "error_patterns.yaml").write_text(
                '- id: compile-hint\n  keywords: ["compile"]\n  guidance: "check compile command"\n',
                encoding="utf-8",
            )
            (knowledge_dir / "cangjie_recipes.md").write_text("", encoding="utf-8")
            (knowledge_dir / "project_conventions.md").write_text("", encoding="utf-8")

            project = ProjectConfig(
                project_name="d5-hybrid",
                project_type="non_ui",
                workdir=str(workdir),
                adapter="cjpm",
                verify_command="cjpm build",
                editable_paths=["src"],
                knowledge_provider="hybrid",
                mcp_server_url="https://mcp.context7.com/mcp",
                mcp_headers=["CONTEXT7_API_KEY=test-key"],
                mcp_tool_name="query-docs",
            )
            policy = PolicyConfig(
                max_iterations=1,
                allow_apply_patch=False,
                require_preflight=False,
                require_knowledge_lookup_on_failure=True,
                require_knowledge_source_evidence=True,
                min_knowledge_hits=1,
            )

            with patch("knowledge.mcp_provider.MCPKnowledgeProvider.retrieve", side_effect=RuntimeError("mcp down")):
                run_loop(
                    base_dir=base_dir,
                    run_id="d5-hybrid-fallback",
                    project=project,
                    policy=policy,
                    adapter=_FailingAdapter(),
                    strategy=_NoopStrategy(),
                    applier=lambda *_args, **_kwargs: PatchResult(
                        applied=False, changed_files=[], changed_lines_per_file={}, message="stub"
                    ),
                    verifier=lambda *_args, **_kwargs: (True, "ok"),
                )

            iter_payload = json.loads(
                (base_dir / "runs" / "d5-hybrid-fallback" / "iter_1.json").read_text(encoding="utf-8")
            )
            self.assertIn("knowledge/error_patterns.yaml", iter_payload["knowledge_sources"])
            decision = iter_payload["knowledge_provider_decision"]
            self.assertEqual(decision["configured_mode"], "hybrid")
            self.assertEqual(decision["selected_provider"], "local")
            self.assertTrue(decision["fallback_used"])
            self.assertEqual(decision["reason"], "mcp_exception")


if __name__ == "__main__":
    unittest.main()
