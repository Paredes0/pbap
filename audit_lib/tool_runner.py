"""
audit_lib.tool_runner — Phase 1 primitive.

Run ONE prediction tool on a FASTA batch and classify the outcome as
OK or PROBLEMATIC. Does NOT parse predictions, does NOT compute metrics,
does NOT retry. Those are later stations of the Phase 1 pipeline.

Env runtime flags (LD_LIBRARY_PATH, USE_TF=0) are load-bearing for some envs
— see docs/deployment.md. Keep ENV_RUNTIME_FLAGS in sync.

Supported run_command interface dimensions (generic, not per-tool wrappers):
  arg_style:
    - "flagged" (default): input via input_flag, output via output_flag.
    - "positional": input as first positional arg (no flag). Output behavior
      still controlled by output_capture / output_flag.
  pre_command:
    - shell string (optional) executed in cwd BEFORE the main script.
      Substitutes "${INPUT}" → absolute peptides_fasta path. Use for tools
      that hardcode an input filename relative to cwd (e.g. apex expects
      ./test_seqs.txt). Non-zero exit → tool returns PROBLEMATIC.
  cwd_subdir:
    - subpath relative to repo_dir (string, optional) used as the working
      directory AND as the script-resolution root. Use for tools whose
      entry-point lives in a subfolder and imports sibling modules with
      bare names (e.g. bert_ampep60/predict/predict.py imports model_def).
      pre_command also runs from this cwd.
  output_capture:
    - "file" (default): script writes to the absolute path passed via
      output_flag. Runner reads from that path.
    - "hardcoded_file": script writes to a fixed filename relative to cwd
      (requires hardcoded_output_name). If output_flag is set, the runner
      passes "output_flag hardcoded_output_name" so scripts that accept a
      filename but always resolve it relative to cwd still work (e.g. hemopi2).
      After a successful run, the runner relocates cwd/hardcoded_output_name
      to the canonical predictions_{tool}.{ext} path.
    - "stdout": script writes its predictions to stdout (no output flag).
      Runner captures stdout and writes it verbatim to the canonical
      predictions_{tool}.{ext} path. Parsing (if any) happens downstream.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from audit_lib.config import get_tool_config, load_pipeline_config

REPO_ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR = REPO_ROOT / "Dataset_Bioactividad" / "Tool_Repos"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "pipeline_config.yaml"
DEFAULT_TIMEOUT_SECONDS = 600

# Some tools require runtime tweaks (e.g. LD_LIBRARY_PATH prepends for CUDA
# libs shipped by their conda env). Paths below resolve at runtime from
# MICROMAMBA_ROOT_PREFIX (or MAMBA_ROOT_PREFIX, or ~/micromamba). Override
# MICROMAMBA_ROOT_PREFIX in your shell if your install lives elsewhere.
import os as _os
_MICROMAMBA_ROOT = _os.environ.get(
    "MICROMAMBA_ROOT_PREFIX",
    _os.environ.get("MAMBA_ROOT_PREFIX", _os.path.expanduser("~/micromamba")),
)

ENV_RUNTIME_FLAGS: dict[str, dict] = {
    "deepb3p_legacy": {
        "ld_library_path_prepend": [
            f"{_MICROMAMBA_ROOT}/envs/deepb3p_legacy/lib/python3.7/site-packages/nvidia/cusparse/lib",
            f"{_MICROMAMBA_ROOT}/envs/deepb3p_legacy/lib/python3.7/site-packages/nvidia/cublas/lib",
        ],
        "env_vars": {"USE_TF": "0"},
    },
}


@dataclass
class ToolResult:
    tool_id: str
    status: Literal["OK", "PROBLEMATIC"]
    predictions_path: Optional[Path]
    diagnosis: Optional[str]
    stderr_tail: Optional[str]
    runtime_seconds: float


def run_tool(
    tool_id: str,
    peptides_fasta: Path,
    output_dir: Path,
    pipeline_config_path: str | Path = DEFAULT_CONFIG_PATH,
    timeout_seconds: Optional[int] = None,
) -> ToolResult:
    """Execute `tool_id` on `peptides_fasta`; return a classified ToolResult."""
    peptides_fasta = Path(peptides_fasta).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_pipeline_config(str(pipeline_config_path))
    try:
        tool_cfg = get_tool_config(tool_id, cfg)
    except KeyError as exc:
        return _fail(tool_id, f"unknown_tool: {exc}", 0.0)

    run_cmd = tool_cfg.get("run_command") or {}
    output_format = run_cmd.get("output_format", "csv")
    predictions_path = output_dir / f"predictions_{tool_id}.{output_format}"
    timeout = timeout_seconds or tool_cfg.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS

    try:
        cmd, cwd, conda_env = _build_command(tool_cfg, tool_id, peptides_fasta, predictions_path)
    except (ValueError, NotImplementedError) as exc:
        return _fail(tool_id, f"config_error: {exc}", 0.0)

    env = _build_env(conda_env)
    t0 = time.monotonic()

    pre_cmd = (tool_cfg.get("run_command") or {}).get("pre_command")
    if pre_cmd:
        rendered = pre_cmd.replace("${INPUT}", str(peptides_fasta))
        try:
            subprocess.run(
                rendered, cwd=str(cwd), env=env, shell=True, check=True,
                capture_output=True, text=True, timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            return _fail(tool_id, f"pre_command_failed: {exc.stderr[-200:] if exc.stderr else exc}", time.monotonic() - t0)
        except subprocess.TimeoutExpired:
            return _fail(tool_id, "pre_command_timeout", time.monotonic() - t0)

    try:
        completed = subprocess.run(
            cmd, cwd=str(cwd), env=env,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return ToolResult(
            tool_id=tool_id, status="PROBLEMATIC", predictions_path=None,
            diagnosis=f"timeout after {timeout}s",
            stderr_tail=_tail(_decode(exc.stderr)),
            runtime_seconds=time.monotonic() - t0,
        )
    except FileNotFoundError as exc:
        return _fail(tool_id, f"launcher_missing: {exc}", time.monotonic() - t0)

    runtime = time.monotonic() - t0
    _persist_logs(output_dir, tool_id, completed.stdout, completed.stderr)

    if completed.returncode != 0:
        return ToolResult(
            tool_id=tool_id, status="PROBLEMATIC", predictions_path=None,
            diagnosis=f"exit_code={completed.returncode}",
            stderr_tail=_tail(completed.stderr), runtime_seconds=runtime,
        )

    run_cmd = tool_cfg.get("run_command") or {}
    if run_cmd.get("output_capture") == "hardcoded_file":
        hardcoded_name = run_cmd.get("hardcoded_output_name")
        src = Path(cwd) / hardcoded_name
        if src.exists():
            shutil.move(str(src), str(predictions_path))
    elif run_cmd.get("output_capture") == "stdout":
        predictions_path.write_text(completed.stdout or "", encoding="utf-8")

    if not predictions_path.exists():
        return ToolResult(
            tool_id=tool_id, status="PROBLEMATIC", predictions_path=None,
            diagnosis=f"output_missing: {predictions_path}",
            stderr_tail=_tail(completed.stderr), runtime_seconds=runtime,
        )
    if predictions_path.stat().st_size == 0:
        return ToolResult(
            tool_id=tool_id, status="PROBLEMATIC", predictions_path=predictions_path,
            diagnosis="output_empty",
            stderr_tail=_tail(completed.stderr), runtime_seconds=runtime,
        )

    return ToolResult(
        tool_id=tool_id, status="OK", predictions_path=predictions_path,
        diagnosis=None, stderr_tail=None, runtime_seconds=runtime,
    )


def _build_command(tool_cfg: dict, tool_id: str, input_path: Path,
                   output_path: Path) -> tuple[list[str], Path, str]:
    run_cmd = tool_cfg.get("run_command") or {}
    cmd_type = run_cmd.get("type", "python_script")
    if cmd_type != "python_script":
        raise NotImplementedError(f"run_command.type={cmd_type!r} not supported yet")
    arg_style = run_cmd.get("arg_style", "flagged")
    if arg_style not in ("flagged", "positional"):
        raise NotImplementedError(f"arg_style={arg_style!r} not supported yet")
    output_capture = run_cmd.get("output_capture", "file")
    if output_capture not in ("file", "hardcoded_file", "stdout"):
        raise NotImplementedError(f"output_capture={output_capture!r} not supported yet")

    conda_env = tool_cfg.get("conda_env", "")
    if not conda_env:
        raise ValueError(f"Tool {tool_id} has no conda_env set")

    repo_dir = _repo_dir_for(tool_cfg, tool_id)
    cwd_subdir = run_cmd.get("cwd_subdir")
    cwd = repo_dir / cwd_subdir if cwd_subdir else repo_dir
    script_path = cwd / run_cmd.get("script", "predict.py")

    # What to pass as the output argument: absolute path (file) or plain name (hardcoded_file).
    if output_capture == "hardcoded_file":
        hardcoded_name = run_cmd.get("hardcoded_output_name")
        if not hardcoded_name:
            raise ValueError(
                f"Tool {tool_id}: output_capture=hardcoded_file requires hardcoded_output_name"
            )
        output_arg = hardcoded_name
    elif output_capture == "stdout":
        output_arg = None
    else:
        output_arg = str(output_path)

    cmd = ["micromamba", "run", "-n", conda_env, "python", str(script_path)]
    if arg_style == "positional":
        cmd += [str(input_path)]
    else:
        input_flag = run_cmd.get("input_flag", "-i")
        if input_flag:
            cmd += [input_flag, str(input_path)]

    output_flag = run_cmd.get("output_flag", "-o")
    if output_flag and output_arg is not None:
        cmd += [output_flag, output_arg]

    cmd += [str(a) for a in (run_cmd.get("extra_args") or [])]
    return cmd, cwd, conda_env


def _repo_dir_for(tool_cfg: dict, tool_id: str) -> Path:
    return REPOS_DIR / tool_id


def _build_env(conda_env: str) -> dict:
    env = os.environ.copy()
    flags = ENV_RUNTIME_FLAGS.get(conda_env, {})
    for ld_path in flags.get("ld_library_path_prepend", []):
        env["LD_LIBRARY_PATH"] = f"{ld_path}:{env.get('LD_LIBRARY_PATH', '')}"
    for key, value in flags.get("env_vars", {}).items():
        env[key] = str(value)
    return env


def _persist_logs(output_dir: Path, tool_id: str, stdout: str, stderr: str) -> None:
    log_path = output_dir / f"run_{tool_id}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(stdout or "")
        f.write("\n=== STDERR ===\n")
        f.write(stderr or "")


def _tail(text: str, n: int = 20) -> str:
    if not text:
        return ""
    return "\n".join(text.rstrip("\n").split("\n")[-n:])


def _decode(b) -> str:
    if b is None:
        return ""
    return b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)


def _fail(tool_id: str, diagnosis: str, runtime: float) -> ToolResult:
    return ToolResult(
        tool_id=tool_id, status="PROBLEMATIC", predictions_path=None,
        diagnosis=diagnosis, stderr_tail=None, runtime_seconds=runtime,
    )
