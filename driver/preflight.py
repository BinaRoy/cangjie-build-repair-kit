from __future__ import annotations

import os
import subprocess
from pathlib import Path

from driver.contracts import PreflightResult, ProjectConfig


def run_preflight(project: ProjectConfig) -> PreflightResult:
    if os.name != "nt":
        return PreflightResult(passed=True, reason="preflight_skipped_non_windows")
    if project.adapter not in ("hvigor", "cjpm"):
        return PreflightResult(passed=True, reason="preflight_skipped_adapter")

    build_tools = _detect_build_tools()
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

    path_parts = _collect_runtime_paths(build_tools)
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

    env = os.environ.copy()
    env["PATH"] = ";".join(path_parts + [env.get("PATH", "")])

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


def _detect_build_tools() -> Path | None:
    cangjie_home = os.environ.get("DEVECO_CANGJIE_HOME", "").strip()
    if cangjie_home:
        p = Path(cangjie_home).resolve()
        candidate = p / "build-tools" if p.name != "build-tools" else p
        if candidate.exists():
            return candidate

    sdk_root = Path.home() / ".cangjie-sdk"
    if not sdk_root.exists():
        return None
    candidates = sorted(sdk_root.glob("*/cangjie/build-tools"))
    return candidates[-1] if candidates else None


def _collect_runtime_paths(build_tools: Path) -> list[str]:
    dirs = [
        build_tools / "bin",
        build_tools / "lib",
        build_tools / "tools" / "bin",
        build_tools / "tools" / "lib",
        build_tools / "third_party" / "llvm" / "bin",
        build_tools / "runtime" / "lib" / "windows_x86_64_cjnative",
    ]
    return [str(p) for p in dirs if p.exists()]


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
