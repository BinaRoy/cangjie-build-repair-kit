from __future__ import annotations

import os
import subprocess
from pathlib import Path

from driver.contracts import PreflightResult, ProjectConfig
from driver.env_setup import build_env_with_toolchain, collect_runtime_paths, detect_build_tools


def run_preflight(project: ProjectConfig) -> PreflightResult:
    if os.name != "nt":
        return PreflightResult(passed=True, reason="preflight_skipped_non_windows")
    if project.adapter not in ("hvigor", "cjpm"):
        return PreflightResult(passed=True, reason="preflight_skipped_adapter")

    build_tools = detect_build_tools()
    if not build_tools:
        return PreflightResult(
            passed=False,
            reason="build_tools_not_found",
            details={
                "hint": "Install Cangjie SDK or set DEVECO_CANGJIE_HOME.",
                "remediation": [
                    "Install Cangjie SDK and ensure ~/.cangjie-sdk/<ver>/cangjie/build-tools exists.",
                    "Set DEVECO_CANGJIE_HOME to your Cangjie SDK root.",
                ],
            },
        )

    path_parts = collect_runtime_paths(build_tools)
    cjpm = build_tools / "tools" / "bin" / "cjpm.exe"
    if not cjpm.exists():
        return PreflightResult(
            passed=False,
            reason="cjpm_missing",
            details={
                "cjpm_path": str(cjpm),
                "remediation": [
                    "Verify SDK installation integrity for build-tools/tools/bin/cjpm.exe.",
                    "Switch DEVECO_CANGJIE_HOME to a healthy SDK version.",
                ],
            },
        )

    env = build_env_with_toolchain()

    proc = subprocess.run(
        [str(cjpm), "--help"],
        cwd=project.workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=min(project.command_timeout_sec, 120),
    )
    if proc.returncode != 0:
        code_hex = hex((proc.returncode + (1 << 32)) % (1 << 32))
        reason = "cjpm_bootstrap_failed"
        hint = ""
        if proc.returncode in (-1073741515, 3221225781):
            reason = "cjpm_bootstrap_failed_missing_dll"
            hint = "Likely missing runtime DLL in PATH (0xC0000135)."
        return PreflightResult(
            passed=False,
            reason=reason,
            details={
                "exit_code": proc.returncode,
                "exit_code_hex": code_hex,
                "cjpm_path": str(cjpm),
                "build_tools": str(build_tools),
                "added_path": path_parts,
                "stderr_head": proc.stderr[:500],
                "hint": hint,
                "remediation": _remediation_for_bootstrap_failure(build_tools, proc.returncode),
            },
        )

    return PreflightResult(
        passed=True,
        reason="ok",
        details={
            "cjpm_path": str(cjpm),
            "build_tools": str(build_tools),
            "added_path": path_parts,
        },
    )


def _remediation_for_bootstrap_failure(build_tools: Path, exit_code: int) -> list[str]:
    base = [
        "Prepend Cangjie runtime/tool dirs to PATH before invoking hvigor/cjpm.",
        f"Suggested build-tools root: {build_tools}",
        "Ensure PATH contains: build-tools/bin; build-tools/lib; build-tools/tools/bin; "
        "build-tools/tools/lib; build-tools/third_party/llvm/bin; "
        "build-tools/runtime/lib/windows_x86_64_cjnative",
    ]
    if exit_code in (-1073741515, 3221225781):
        base.append("Exit code maps to 0xC0000135 (missing DLL). Fix PATH or reinstall SDK runtime.")
    return base
