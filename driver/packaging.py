from __future__ import annotations

import shutil
from pathlib import Path


INCLUDE_DIRS = [
    "driver",
    "adapters",
    "repair",
    "knowledge",
    "configs",
    "prompts",
    "examples",
    "docs",
]

INCLUDE_FILES = [
    "README.md",
    "pyproject.toml",
]

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".hvigor",
    "runs",
    "logs",
    "tmp_init",
    "cangjie_repair_template.egg-info",
}

EXCLUDE_REL_PREFIXES = [
    "knowledge/external",
]


def export_product_bundle(base_dir: Path, output_dir: Path, force: bool) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        if not force:
            raise FileExistsError(f"Output already exists: {output_dir}. Use --force to overwrite.")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel in INCLUDE_DIRS:
        src = base_dir / rel
        if src.exists():
            _copy_tree_filtered(base_dir, src, output_dir / rel)

    for rel in INCLUDE_FILES:
        src = base_dir / rel
        if src.exists():
            dst = output_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    _write_bootstrap_scripts(output_dir / "scripts")
    _write_product_readme(output_dir)
    return output_dir


def _copy_tree_filtered(base_dir: Path, src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(base_dir).as_posix()
        if _should_exclude(path, rel):
            continue
        target = dst / path.relative_to(src)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _should_exclude(path: Path, rel: str) -> bool:
    parts = set(path.parts)
    if EXCLUDE_DIR_NAMES.intersection(parts):
        return True
    for prefix in EXCLUDE_REL_PREFIXES:
        if rel.startswith(prefix):
            return True
    return False


def _write_bootstrap_scripts(scripts_dir: Path) -> None:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    ps1 = scripts_dir / "bootstrap_knowledge.ps1"
    sh = scripts_dir / "bootstrap_knowledge.sh"
    ps1.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "$base = Join-Path $PSScriptRoot '..\\knowledge\\external'",
                "New-Item -ItemType Directory -Force -Path $base | Out-Null",
                "$repos = @(",
                "  'https://gitcode.com/Cangjie/cangjie_tools.git',",
                "  'https://gitcode.com/Cangjie/cangjie_compiler.git',",
                "  'https://gitcode.com/Cangjie/cangjie_runtime.git',",
                "  'https://gitcode.com/Cangjie/cangjie_docs.git'",
                ")",
                "foreach ($repo in $repos) {",
                "  $name = [System.IO.Path]::GetFileNameWithoutExtension($repo)",
                "  $dst = Join-Path $base $name",
                "  if (Test-Path $dst) { Write-Host \"skip $name (exists)\"; continue }",
                "  git clone $repo $dst",
                "}",
                "Write-Host 'knowledge bootstrap completed.'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    sh.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "BASE_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)/../knowledge/external\"",
                "mkdir -p \"$BASE_DIR\"",
                "repos=(",
                "  \"https://gitcode.com/Cangjie/cangjie_tools.git\"",
                "  \"https://gitcode.com/Cangjie/cangjie_compiler.git\"",
                "  \"https://gitcode.com/Cangjie/cangjie_runtime.git\"",
                "  \"https://gitcode.com/Cangjie/cangjie_docs.git\"",
                ")",
                "for repo in \"${repos[@]}\"; do",
                "  name=\"$(basename \"$repo\" .git)\"",
                "  dst=\"$BASE_DIR/$name\"",
                "  if [ -d \"$dst\" ]; then",
                "    echo \"skip $name (exists)\"",
                "    continue",
                "  fi",
                "  git clone \"$repo\" \"$dst\"",
                "done",
                "echo \"knowledge bootstrap completed.\"",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_product_readme(output_dir: Path) -> None:
    path = output_dir / "PRODUCT_PACKAGING.md"
    path.write_text(
        "\n".join(
            [
                "# Product Packaging Notes",
                "",
                "## Included",
                "- Core engine: driver/adapters/repair",
                "- Config templates: configs/",
                "- Lightweight knowledge and lookup rules: knowledge/ (excluding external mirrors)",
                "- CLI entry and docs",
                "- Minimal examples",
                "",
                "## Excluded",
                "- Runtime artifacts: runs/, logs/",
                "- IDE/cache folders",
                "- External mirrored repos under knowledge/external/",
                "",
                "## Restore external knowledge",
                "- PowerShell: `scripts/bootstrap_knowledge.ps1`",
                "- Bash: `scripts/bootstrap_knowledge.sh`",
                "",
            ]
        ),
        encoding="utf-8",
    )
