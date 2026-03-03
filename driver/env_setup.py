from __future__ import annotations

import os
from pathlib import Path


def detect_build_tools() -> Path | None:
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


def collect_runtime_paths(build_tools: Path) -> list[str]:
    dirs = [
        build_tools / "bin",
        build_tools / "lib",
        build_tools / "tools" / "bin",
        build_tools / "tools" / "lib",
        build_tools / "third_party" / "llvm" / "bin",
        build_tools / "runtime" / "lib" / "windows_x86_64_cjnative",
    ]
    return [str(p) for p in dirs if p.exists()]


def build_env_with_toolchain(base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    if os.name != "nt":
        return env
    bt = detect_build_tools()
    if not bt:
        return env
    runtime_paths = collect_runtime_paths(bt)
    if runtime_paths:
        env["PATH"] = ";".join(runtime_paths + [env.get("PATH", "")])
    return env
