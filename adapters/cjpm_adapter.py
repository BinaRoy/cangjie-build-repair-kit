from __future__ import annotations

import subprocess
import time
from pathlib import Path

from adapters.base import BuildAdapter
from driver.contracts import ProjectConfig, VerifyResult
from driver.env_setup import build_env_with_toolchain


class CjpmAdapter(BuildAdapter):
    def verify(self, project: ProjectConfig) -> VerifyResult:
        start = time.time()
        proc = subprocess.run(
            project.verify_command,
            cwd=Path(project.workdir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=project.command_timeout_sec,
            encoding="utf-8",
            errors="replace",
            env=build_env_with_toolchain(),
        )
        return VerifyResult(
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            duration_sec=round(time.time() - start, 3),
            command=project.verify_command,
            stdout=proc.stdout,
            stderr=proc.stderr,
            artifact_checks={},
        )
