from __future__ import annotations

import subprocess
import time
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ProjectConfig, VerifyResult
from driver.env_setup import build_env_with_toolchain


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
        output = [f"[build] $ {project.verify_command}", build_proc.stdout, build_proc.stderr]
        command = project.verify_command
        final_code = build_proc.returncode
        final_success = build_proc.returncode == 0

        if final_success and project.test_command.strip():
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
            output.extend([f"[test] $ {project.test_command}", test_proc.stdout, test_proc.stderr])
            command = f"{project.verify_command} && {project.test_command}"
            final_code = test_proc.returncode
            final_success = test_proc.returncode == 0

        checks = {}
        for rel in project.artifact_checks:
            checks[rel] = (Path(project.workdir) / rel).exists()
        if checks:
            final_success = final_success and all(checks.values())
        return VerifyResult(
            success=final_success,
            exit_code=final_code,
            duration_sec=round(time.time() - start, 3),
            command=command,
            stdout="\n".join([x for x in output if x and x.strip()]),
            stderr="",
            artifact_checks=checks,
        )
