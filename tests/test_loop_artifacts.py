from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import PolicyConfig, ProjectConfig, VerifyResult
from driver.loop import run_loop


class _FailingAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        return VerifyResult(
            success=False,
            exit_code=2,
            duration_sec=0.01,
            command=project.verify_command,
            stdout="",
            stderr="src/main.cj:12:5 error: undefined symbol MainAbility",
            artifact_checks={},
        )


class LoopArtifactTests(unittest.TestCase):
    def test_run_loop_writes_error_and_patch_plan_per_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workdir = base_dir / "work"
            (workdir / "src").mkdir(parents=True)

            project = ProjectConfig(
                project_name="x",
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

            run_loop(base_dir=base_dir, run_id="loop-a5", project=project, policy=policy, adapter=_FailingAdapter())

            run_dir = base_dir / "runs" / "loop-a5"
            error_path = run_dir / "error_iter_1.json"
            plan_path = run_dir / "patch_plan_iter_1.json"
            iter_path = run_dir / "iter_1.json"

            self.assertTrue(error_path.exists())
            self.assertTrue(plan_path.exists())
            self.assertTrue(iter_path.exists())

            error_payload = json.loads(error_path.read_text(encoding="utf-8"))
            plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
            iter_payload = json.loads(iter_path.read_text(encoding="utf-8"))
            self.assertIn("fingerprint", error_payload)
            self.assertIn("category", error_payload)
            self.assertIn("can_apply", plan_payload)
            self.assertIn("diff_summary", plan_payload)
            self.assertIn("knowledge_sources", iter_payload)
            self.assertIn("knowledge_provider_decision", iter_payload)
            self.assertIn("model_route_decision", iter_payload)
            self.assertIsInstance(iter_payload["knowledge_sources"], list)
            self.assertIsInstance(iter_payload["knowledge_provider_decision"], dict)
            self.assertIsInstance(iter_payload["model_route_decision"], dict)
            self.assertIn("configured_mode", iter_payload["knowledge_provider_decision"])
            self.assertIn("provider_name", iter_payload["knowledge_provider_decision"])


if __name__ == "__main__":
    unittest.main()
