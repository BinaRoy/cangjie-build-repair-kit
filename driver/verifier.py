from __future__ import annotations

from pathlib import Path

from driver.contracts import VerifyResult


def evaluate_verify_result(
    workdir: Path,
    build_returncode: int,
    build_stdout: str,
    build_stderr: str,
    build_command: str,
    test_returncode: int | None,
    test_stdout: str,
    test_stderr: str,
    test_command: str,
    artifact_checks: list[str],
) -> VerifyResult:
    output = [f"[build] $ {build_command}", build_stdout, build_stderr]
    final_code = build_returncode
    final_success = build_returncode == 0
    command = build_command

    if final_success and test_returncode is not None:
        output.extend([f"[test] $ {test_command}", test_stdout, test_stderr])
        final_code = test_returncode
        final_success = test_returncode == 0
        command = f"{build_command} && {test_command}"

    checks: dict[str, bool] = {}
    if final_success:
        for rel in artifact_checks:
            checks[rel] = (workdir / rel).exists()
        if checks:
            final_success = final_success and all(checks.values())

    return VerifyResult(
        success=final_success,
        exit_code=final_code,
        duration_sec=0.0,
        command=command,
        stdout="\n".join([x for x in output if x and x.strip()]),
        stderr="",
        artifact_checks=checks,
    )
