from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import shutil
import uuid
from pathlib import Path
from typing import Sequence

from adapters.cjpm_adapter import CjpmAdapter
from adapters.hvigor_adapter import HvigorAdapter
from driver.contracts import PolicyConfig, ProjectConfig
from driver.env_setup import build_env_with_toolchain
from driver.loop import run_loop
from driver.packaging import export_product_bundle
from driver.reporting import generate_run_report


def _load_toml(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    try:
        import tomllib  # py3.11+

        return tomllib.loads(raw)
    except ModuleNotFoundError:
        return _parse_simple_toml(raw)


def _parse_simple_toml(text: str) -> dict:
    data: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        data[key] = _parse_toml_value(val)
    return data


def _parse_toml_value(val: str):
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip('"') for x in inner.split(",")]
    try:
        return int(val)
    except ValueError:
        return val


def _expand_env_vars(value):
    if isinstance(value, str):
        # Supports ${VAR} style placeholders.
        def repl(match):
            key = match.group(1)
            return os.environ.get(key, match.group(0))

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, value)
    if isinstance(value, list):
        return [_expand_env_vars(x) for x in value]
    return value


def _normalize_project_config(project_data: dict, project_config_path: Path) -> dict:
    out = {k: _expand_env_vars(v) for k, v in project_data.items()}
    wd = str(out.get("workdir", ".")).strip() or "."
    wd_path = Path(wd)
    if not wd_path.is_absolute():
        wd_path = (project_config_path.parent / wd_path).resolve()
    out["workdir"] = wd_path.as_posix()
    return out


def _pick_adapter(name: str):
    if name == "hvigor":
        return HvigorAdapter()
    if name == "cjpm":
        return CjpmAdapter()
    raise ValueError(f"Unsupported adapter: {name}")


def _default_run_id() -> str:
    return f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}_{uuid.uuid4().hex[:6]}"


def _run_command(project_config: str, policy_config: str, run_id: str = "") -> int:
    base_dir = Path(__file__).resolve().parents[1]
    project_cfg_path = Path(project_config).resolve()
    project_data = _normalize_project_config(_load_toml(project_cfg_path), project_cfg_path)
    policy_data = _load_toml(Path(policy_config))

    project = ProjectConfig(**project_data)
    policy = PolicyConfig(**policy_data)
    rid = run_id or _default_run_id()
    adapter = _pick_adapter(project.adapter)

    summary = run_loop(
        base_dir=base_dir,
        run_id=rid,
        project=project,
        policy=policy,
        adapter=adapter,
    )
    report_path = generate_run_report(base_dir / "runs" / summary.run_id)
    print(
        f"run_id={summary.run_id} status={summary.final_status} "
        f"reason={summary.stop_reason} report={report_path.as_posix()}"
    )
    return 0 if summary.final_status == "success" else 1


def _validate_schema(project_config: str, policy_config: str) -> tuple[ProjectConfig, PolicyConfig]:
    project_cfg_path = Path(project_config).resolve()
    project_data = _normalize_project_config(_load_toml(project_cfg_path), project_cfg_path)
    policy_data = _load_toml(Path(policy_config))
    return ProjectConfig(**project_data), PolicyConfig(**policy_data)


def _looks_like_path_token(token: str) -> bool:
    return (
        "/" in token
        or "\\" in token
        or token.lower().endswith((".cmd", ".bat", ".ps1", ".sh", ".py", ".exe"))
    )


def _extract_required_commands(command: str) -> list[str]:
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        return []
    if not tokens:
        return []

    required = [tokens[0]]
    wrappers = {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe", "bash", "sh"}
    head = tokens[0].lower()
    if head in wrappers and len(tokens) > 1:
        marker_index = None
        if head.startswith("cmd"):
            for i, token in enumerate(tokens[1:], start=1):
                if token.lower() in ("/c", "/k"):
                    marker_index = i
                    break
        else:
            for i, token in enumerate(tokens[1:], start=1):
                if token in ("-c", "-Command", "-command", "-File", "-file"):
                    marker_index = i
                    break
        if marker_index is not None and marker_index + 1 < len(tokens):
            nested = tokens[marker_index + 1]
            nested_cmds = _extract_required_commands(nested)
            if nested_cmds:
                required.extend(nested_cmds)
            else:
                required.append(nested)
        elif len(tokens) > 1:
            required.append(tokens[1])
    return required


def _check_command_availability(command: str, workdir: Path) -> list[str]:
    issues: list[str] = []
    candidates = _extract_required_commands(command)
    if not candidates:
        return ["verify_command is empty or cannot be parsed"]

    env = build_env_with_toolchain()
    for token in candidates:
        if _looks_like_path_token(token):
            token_path = Path(token)
            if not token_path.is_absolute():
                token_path = (workdir / token_path).resolve()
            if not token_path.exists():
                issues.append(f"command path not found: {token_path.as_posix()}")
        else:
            if shutil.which(token, path=env.get("PATH")) is None:
                issues.append(f"command not found in PATH: {token}")
    return issues


def _resolve_path_issue(rel: str, workdir: Path, label: str) -> str | None:
    p = (workdir / rel).resolve()
    if not p.exists():
        return f"{label} not found: {p.as_posix()}"
    return None


def _validate_command(project_config: str, policy_config: str) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        project, _ = _validate_schema(project_config, policy_config)
    except Exception as exc:
        print(f"validate: FAIL schema error: {exc}")
        return 1

    workdir = Path(project.workdir).resolve()
    if not workdir.exists():
        errors.append(f"workdir not found: {workdir.as_posix()}")
    elif not workdir.is_dir():
        errors.append(f"workdir is not a directory: {workdir.as_posix()}")

    for rel in project.editable_paths:
        issue = _resolve_path_issue(rel, workdir, "editable path")
        if issue:
            errors.append(issue)
    for rel in project.readonly_paths:
        issue = _resolve_path_issue(rel, workdir, "readonly path")
        if issue:
            warnings.append(issue)
    for rel in project.artifact_checks:
        p = (workdir / rel).resolve()
        if not p.exists():
            warnings.append(f"artifact missing before build: {p.as_posix()}")

    if workdir.exists() and workdir.is_dir():
        errors.extend(_check_command_availability(project.verify_command, workdir))
        if project.test_command.strip():
            errors.extend(_check_command_availability(project.test_command, workdir))

    if errors:
        print("validate: FAIL")
        for msg in errors:
            print(f"- error: {msg}")
        for msg in warnings:
            print(f"- warning: {msg}")
        return 1

    print("validate: OK")
    print(f"- project: {project.project_name}")
    print(f"- workdir: {workdir.as_posix()}")
    if warnings:
        for msg in warnings:
            print(f"- warning: {msg}")
    return 0


def _init_command(template: str, output_dir: str, project_name: str, workdir: str, force: bool) -> int:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    proj_path = out / f"project.{project_name}.toml"
    policy_path = out / "policy.default.toml"

    if (proj_path.exists() or policy_path.exists()) and not force:
        raise FileExistsError(f"Config exists in {out}. Use --force to overwrite.")

    wd = workdir.replace("\\", "/")
    if template == "ui":
        project = (
            f'project_name = "{project_name}"\n'
            'project_type = "ui"\n'
            f'workdir = "{wd}"\n'
            'adapter = "hvigor"\n'
            'verify_command = "hvigorw.bat --mode module -p module=entry -p product=default clean assembleHap --no-daemon"\n'
            'test_command = "hvigorw.bat --mode module -p module=entry -p product=default test --no-daemon"\n'
            "command_timeout_sec = 1200\n"
            'editable_paths = ["entry/src/main/cangjie", "entry/cjpm.toml"]\n'
            'readonly_paths = ["AppScope", ".hvigor", "oh_modules"]\n'
            'artifact_checks = ["entry/build/default/outputs/default/entry-default-unsigned.hap"]\n'
        )
    else:
        project = (
            f'project_name = "{project_name}"\n'
            'project_type = "non_ui"\n'
            f'workdir = "{wd}"\n'
            'adapter = "cjpm"\n'
            'verify_command = "cjpm build"\n'
            'test_command = "cjpm test"\n'
            "command_timeout_sec = 600\n"
            'editable_paths = ["src", "cjpm.toml"]\n'
            'readonly_paths = ["target", ".git", "build"]\n'
            "artifact_checks = []\n"
        )

    policy = (
        "max_iterations = 4\n"
        "max_files_changed_per_iter = 2\n"
        "max_total_files_changed = 6\n"
        "max_changed_lines_per_file = 120\n"
        "same_error_max_repeat = 2\n"
        "require_root_cause_extracted = true\n"
        "require_diff_summary = true\n"
        "stop_on_new_error_family = false\n"
        "allow_apply_patch = true\n"
        "require_verify_pass_after_patch = true\n"
        "require_preflight = true\n"
        "require_knowledge_lookup_on_failure = true\n"
        "min_knowledge_hits = 1\n"
        "require_knowledge_source_evidence = true\n"
        "require_non_scaffold_patch = true\n"
        "min_changed_lines_when_patch_applied = 1\n"
        'scaffold_markers = ["TODO", "FIXME", "NotImplemented", "stub", "placeholder"]\n'
    )

    proj_path.write_text(project, encoding="utf-8")
    policy_path.write_text(policy, encoding="utf-8")
    print(f"generated project config: {proj_path.as_posix()}")
    print(f"generated policy config: {policy_path.as_posix()}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cangjie build-repair tool")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run build-repair loop")
    run.add_argument("--project-config", required=True)
    run.add_argument("--policy-config", required=True)
    run.add_argument("--run-id", default="")

    init = sub.add_parser("init", help="generate reusable config templates")
    init.add_argument("--template", choices=["ui", "non_ui"], required=True)
    init.add_argument("--output-dir", required=True)
    init.add_argument("--project-name", default="sample")
    init.add_argument("--workdir", default="")
    init.add_argument("--force", action="store_true")

    export = sub.add_parser("export", help="export product bundle with filtered content")
    export.add_argument("--output-dir", required=True)
    export.add_argument("--force", action="store_true")

    validate = sub.add_parser("validate", help="validate config schema and command/path availability")
    validate.add_argument("--project-config", required=True)
    validate.add_argument("--policy-config", required=True)

    # Legacy mode compatibility: supports old direct run flags.
    parser.add_argument("--project-config")
    parser.add_argument("--policy-config")
    parser.add_argument("--run-id", default="")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    base_dir = Path(__file__).resolve().parents[1]
    if args.command == "init":
        workdir = args.workdir or "."
        return _init_command(args.template, args.output_dir, args.project_name, workdir, args.force)
    if args.command == "export":
        out = export_product_bundle(base_dir=base_dir, output_dir=Path(args.output_dir), force=args.force)
        print(f"exported product bundle: {out.as_posix()}")
        return 0
    if args.command == "validate":
        return _validate_command(args.project_config, args.policy_config)
    if args.command == "run":
        return _run_command(args.project_config, args.policy_config, args.run_id)

    # Legacy fallback: keep existing scripts working.
    if args.project_config and args.policy_config:
        return _run_command(args.project_config, args.policy_config, args.run_id)
    raise SystemExit(
        "Use `run`, `validate`, `init` or `export` subcommand. "
        "Example: cangjie-repair run --project-config ..."
    )


if __name__ == "__main__":
    raise SystemExit(main())
