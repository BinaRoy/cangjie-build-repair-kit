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
from driver.doc_maintenance import append_update_entry
from driver.env_setup import build_env_with_toolchain
from driver.issue_autopilot import run_issue_autopilot
from driver.loop import run_loop
from driver.packaging import export_product_bundle
from driver.reporting import generate_run_report
from driver.session_snapshot import write_snapshot_file
from driver.weekly_report import generate_weekly_comparison_report


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
            'knowledge_provider = "local"\n'
            'mcp_server_command = ""\n'
            "mcp_server_args = []\n"
            'mcp_server_url = ""\n'
            "mcp_headers = []\n"
            'mcp_tool_name = "query-docs"\n'
            "mcp_timeout_sec = 15\n"
            "mcp_max_items = 5\n"
            'repair_strategy = "rule_based"\n'
            'llm_api_url = ""\n'
            'llm_api_key = ""\n'
            'llm_model = ""\n'
            'llm_model_secondary = ""\n'
            'llm_route_rule = "error_type_or_complexity"\n'
            'llm_secondary_categories = ["syntax", "generic", "type"]\n'
            "llm_complexity_threshold = 220\n"
            "llm_timeout_sec = 30\n"
            "llm_temperature = 0.0\n"
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
            'knowledge_provider = "local"\n'
            'mcp_server_command = ""\n'
            "mcp_server_args = []\n"
            'mcp_server_url = ""\n'
            "mcp_headers = []\n"
            'mcp_tool_name = "query-docs"\n'
            "mcp_timeout_sec = 15\n"
            "mcp_max_items = 5\n"
            'repair_strategy = "rule_based"\n'
            'llm_api_url = ""\n'
            'llm_api_key = ""\n'
            'llm_model = ""\n'
            'llm_model_secondary = ""\n'
            'llm_route_rule = "error_type_or_complexity"\n'
            'llm_secondary_categories = ["syntax", "generic", "type"]\n'
            "llm_complexity_threshold = 220\n"
            "llm_timeout_sec = 30\n"
            "llm_temperature = 0.0\n"
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
        "similar_case_top_k = 3\n"
        'scaffold_markers = ["TODO", "FIXME", "NotImplemented", "stub", "placeholder"]\n'
    )

    proj_path.write_text(project, encoding="utf-8")
    policy_path.write_text(policy, encoding="utf-8")
    print(f"generated project config: {proj_path.as_posix()}")
    print(f"generated policy config: {policy_path.as_posix()}")
    return 0


def _snapshot_command(output: str, source_doc: str) -> int:
    base_dir = Path(__file__).resolve().parents[1]
    out = Path(output).resolve()
    source = Path(source_doc).resolve()
    path = write_snapshot_file(base_dir=base_dir, source_doc=source, output_path=out)
    print(f"session snapshot generated: {path.as_posix()}")
    return 0


def _doc_update_command(
    doc_path: str,
    date_text: str,
    change: str,
    modules: str,
    verify_command: str,
    result: str,
    risk: str,
) -> int:
    mods = [x.strip() for x in modules.split(",") if x.strip()]
    out = append_update_entry(
        doc_path=Path(doc_path).resolve(),
        date_text=date_text,
        change=change,
        modules=mods,
        verify_command=verify_command,
        result=result,
        risk=risk,
    )
    print(f"development update appended: {out.as_posix()}")
    return 0


def _bootstrap_non_ui(project_root: str, output_dir: str, project_name: str, force: bool) -> int:
    root = Path(project_root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"bootstrap-nonui: FAIL project root not found: {root.as_posix()}")
        return 1

    rc = _init_command("non_ui", output_dir, project_name, root.as_posix(), force)
    if rc != 0:
        return rc

    out = Path(output_dir).resolve()
    project_path = out / f"project.{project_name}.toml"
    policy_path = out / "policy.default.toml"
    guide_path = out / "FOLLOW_GUIDE.md"

    project_cfg = _load_toml(project_path)
    detected_editables = [p for p in ["src", "source", "lib", "cjpm.toml"] if (root / p).exists()]
    if detected_editables:
        project_cfg["editable_paths"] = detected_editables
    else:
        project_cfg["editable_paths"] = ["src", "cjpm.toml"]

    if not (root / "cjpm.toml").exists():
        project_cfg["verify_command"] = "<fill_verify_command>"
        project_cfg["test_command"] = ""

    _write_simple_toml(project_path, project_cfg)

    guide_lines = [
        "# Non-UI Project Follow Guide",
        "",
        "## 1) Check generated files",
        f"- Project config: `{project_path.as_posix()}`",
        f"- Policy config: `{policy_path.as_posix()}`",
        "",
        "## 2) Fill project-specific fields (required)",
        "- `verify_command` (build command)",
        "- `test_command` (optional but recommended)",
        "- `editable_paths` (already auto-detected, verify before run)",
        "",
        "## 3) Validate",
        f"`python3 -m driver.main validate --project-config {project_path.as_posix()} --policy-config {policy_path.as_posix()}`",
        "",
        "## 4) Run repair loop",
        f"`python3 -m driver.main run --project-config {project_path.as_posix()} --policy-config {policy_path.as_posix()}`",
        "",
        "## 5) Inspect outputs",
        "- `runs/<run_id>/summary.json`",
        "- `runs/<run_id>/report.md`",
        "- `runs/<run_id>/iter_*.json`",
    ]
    guide_path.write_text("\n".join(guide_lines) + "\n", encoding="utf-8")
    print(f"bootstrap guide generated: {guide_path.as_posix()}")
    return 0


def _write_simple_toml(path: Path, data: dict) -> None:
    lines: list[str] = []
    order = [
        "project_name",
        "project_type",
        "workdir",
        "adapter",
        "verify_command",
        "test_command",
        "command_timeout_sec",
        "knowledge_provider",
        "mcp_server_command",
        "mcp_server_args",
        "mcp_server_url",
        "mcp_headers",
        "mcp_tool_name",
        "mcp_timeout_sec",
        "mcp_max_items",
        "repair_strategy",
        "llm_api_url",
        "llm_api_key",
        "llm_model",
        "llm_model_secondary",
        "llm_route_rule",
        "llm_secondary_categories",
        "llm_complexity_threshold",
        "llm_timeout_sec",
        "llm_temperature",
        "editable_paths",
        "readonly_paths",
        "artifact_checks",
    ]
    for key in order:
        if key in data:
            lines.append(f"{key} = {_toml_serialize_value(data[key])}")
    for key, value in data.items():
        if key not in order:
            lines.append(f"{key} = {_toml_serialize_value(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _toml_serialize_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(f'"{item}"')
            elif isinstance(item, bool):
                out.append("true" if item else "false")
            else:
                out.append(str(item))
        return "[" + ", ".join(out) + "]"
    return f'"{str(value)}"'


def _weekly_report_command(runs_dir: str, output: str, days: int) -> int:
    out = generate_weekly_comparison_report(
        runs_dir=Path(runs_dir).resolve(),
        output_path=Path(output).resolve(),
        days=days,
    )
    print(f"weekly report generated: {out.as_posix()}")
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

    snapshot = sub.add_parser("snapshot", help="generate session snapshot for next context handoff")
    snapshot.add_argument("--output", default="docs/session_snapshot.md")
    snapshot.add_argument("--source-doc", default="docs/development_assessment_and_followup.md")

    doc_update = sub.add_parser("doc-update", help="append one update entry to development followup doc")
    doc_update.add_argument("--doc-path", default="docs/development_assessment_and_followup.md")
    doc_update.add_argument("--date", required=True)
    doc_update.add_argument("--change", required=True)
    doc_update.add_argument("--modules", default="")
    doc_update.add_argument("--verify-command", required=True)
    doc_update.add_argument("--result", required=True)
    doc_update.add_argument("--risk", default="")

    validate = sub.add_parser("validate", help="validate config schema and command/path availability")
    validate.add_argument("--project-config", required=True)
    validate.add_argument("--policy-config", required=True)

    weekly = sub.add_parser("weekly-report", help="generate weekly model comparison report")
    weekly.add_argument("--runs-dir", default="runs")
    weekly.add_argument("--output", default="docs/weekly_model_report.md")
    weekly.add_argument("--days", type=int, default=7)

    bootstrap = sub.add_parser("bootstrap-nonui", help="bootstrap configs for a new non-ui project")
    bootstrap.add_argument("--project-root", required=True)
    bootstrap.add_argument("--output-dir", required=True)
    bootstrap.add_argument("--project-name", default="sample")
    bootstrap.add_argument("--force", action="store_true")

    autopilot = sub.add_parser("issue-autopilot", help="auto-run issue -> coding -> test -> PR flow")
    autopilot.add_argument("--issue-number", required=True, type=int)
    autopilot.add_argument("--base-branch", default="main")
    autopilot.add_argument("--test-command", default="python3 -m unittest discover -s tests -q")
    autopilot.add_argument("--skip-codex", action="store_true")
    autopilot.add_argument("--no-pr", action="store_true")
    autopilot.add_argument("--no-push", action="store_true")

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
    if args.command == "snapshot":
        return _snapshot_command(args.output, args.source_doc)
    if args.command == "doc-update":
        return _doc_update_command(
            doc_path=args.doc_path,
            date_text=args.date,
            change=args.change,
            modules=args.modules,
            verify_command=args.verify_command,
            result=args.result,
            risk=args.risk,
        )
    if args.command == "validate":
        return _validate_command(args.project_config, args.policy_config)
    if args.command == "weekly-report":
        return _weekly_report_command(args.runs_dir, args.output, args.days)
    if args.command == "bootstrap-nonui":
        return _bootstrap_non_ui(args.project_root, args.output_dir, args.project_name, args.force)
    if args.command == "issue-autopilot":
        return run_issue_autopilot(
            issue_number=args.issue_number,
            base_branch=args.base_branch,
            test_command=args.test_command,
            run_codex=not args.skip_codex,
            create_pr=not args.no_pr,
            push_branch=not args.no_push,
        )
    if args.command == "run":
        return _run_command(args.project_config, args.policy_config, args.run_id)

    # Legacy fallback: keep existing scripts working.
    if args.project_config and args.policy_config:
        return _run_command(args.project_config, args.policy_config, args.run_id)
    raise SystemExit(
        "Use `run`, `validate`, `init`, `export`, `snapshot`, `doc-update`, `weekly-report`, `bootstrap-nonui` or `issue-autopilot` subcommand. "
        "Example: cangjie-repair run --project-config ..."
    )


if __name__ == "__main__":
    raise SystemExit(main())
