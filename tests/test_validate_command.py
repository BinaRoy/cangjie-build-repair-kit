from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

from driver.main import _extract_required_commands, _validate_command


class ValidateCommandTests(unittest.TestCase):
    def test_extract_required_commands_for_wrapped_command(self) -> None:
        self.assertEqual(_extract_required_commands("cmd /c run_hvigor.cmd"), ["cmd", "run_hvigor.cmd"])

    def test_validate_command_passes_for_valid_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            (workdir / "src").mkdir(parents=True)
            (workdir / "readonly").mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "ok-project"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        f'verify_command = "{sys.executable} --version"',
                        "command_timeout_sec = 60",
                        'editable_paths = ["src"]',
                        'readonly_paths = ["readonly"]',
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 0)

    def test_validate_command_fails_when_command_or_path_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            workdir.mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "bad-project"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        'verify_command = "definitely_missing_command_123456 --help"',
                        "command_timeout_sec = 60",
                        'editable_paths = ["missing_src"]',
                        "readonly_paths = []",
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 1)

    def test_validate_command_fails_when_test_command_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            (workdir / "src").mkdir(parents=True)
            (workdir / "readonly").mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "bad-test-command"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        f'verify_command = "{sys.executable} --version"',
                        'test_command = "definitely_missing_test_cmd_123456 --help"',
                        "command_timeout_sec = 60",
                        'editable_paths = ["src"]',
                        'readonly_paths = ["readonly"]',
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 1)

    def test_validate_command_fails_for_invalid_knowledge_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            (workdir / "src").mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "bad-provider"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        f'verify_command = "{sys.executable} --version"',
                        'knowledge_provider = "invalid_mode"',
                        'editable_paths = ["src"]',
                        "readonly_paths = []",
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 1)

    def test_validate_command_fails_for_invalid_repair_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            (workdir / "src").mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "bad-strategy"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        f'verify_command = "{sys.executable} --version"',
                        'repair_strategy = "bad_mode"',
                        'editable_paths = ["src"]',
                        "readonly_paths = []",
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 1)

    def test_validate_command_fails_for_invalid_llm_route_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "work"
            (workdir / "src").mkdir(parents=True)

            project_cfg = root / "project.toml"
            policy_cfg = root / "policy.toml"
            project_cfg.write_text(
                "\n".join(
                    [
                        'project_name = "bad-route-rule"',
                        'project_type = "non_ui"',
                        f'workdir = "{workdir.as_posix()}"',
                        'adapter = "cjpm"',
                        f'verify_command = "{sys.executable} --version"',
                        'repair_strategy = "multi_llm"',
                        'llm_route_rule = "not_supported"',
                        'editable_paths = ["src"]',
                        "readonly_paths = []",
                        "artifact_checks = []",
                    ]
                ),
                encoding="utf-8",
            )
            policy_cfg.write_text("", encoding="utf-8")

            self.assertEqual(_validate_command(str(project_cfg), str(policy_cfg)), 1)


if __name__ == "__main__":
    unittest.main()
