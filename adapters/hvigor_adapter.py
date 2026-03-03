from __future__ import annotations

import subprocess
import time
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ProjectConfig, VerifyResult
from driver.env_setup import build_env_with_toolchain
from driver.verifier import evaluate_verify_result


class HvigorAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        start = time.time()
        env = build_env_with_toolchain()
        build_proc = subprocess.run(
            project.verify_command,
            cwd=Path(project.workdir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=project.command_timeout_sec,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        test_returncode = None
        test_stdout = ""
        test_stderr = ""
        if build_proc.returncode == 0 and project.test_command.strip():
            test_proc = subprocess.run(
                project.test_command,
                cwd=Path(project.workdir),
                shell=True,
                capture_output=True,
                text=True,
                timeout=project.command_timeout_sec,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            test_returncode = test_proc.returncode
            test_stdout = test_proc.stdout
            test_stderr = test_proc.stderr

        result = evaluate_verify_result(
            workdir=Path(project.workdir),
            build_returncode=build_proc.returncode,
            build_stdout=build_proc.stdout,
            build_stderr=build_proc.stderr,
            build_command=project.verify_command,
            test_returncode=test_returncode,
            test_stdout=test_stdout,
            test_stderr=test_stderr,
            test_command=project.test_command,
            artifact_checks=project.artifact_checks,
        )
        result.duration_sec = round(time.time() - start, 3)
        return result
