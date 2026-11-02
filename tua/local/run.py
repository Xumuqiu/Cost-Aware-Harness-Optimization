"""Run README ablations on the previous fixed 40 tasks, with bounded parallel jobs."""

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

import yaml

from tua.local.runtime import bundles

REPO = Path(__file__).resolve().parents[2]
LOCAL = Path(__file__).resolve().parent
RUNTIME = LOCAL / ".runtime"
SUBSET = LOCAL / "subset-previous40.json"
MAIN = ["B0-qwen", "B1-dsflash", *[f"A{i}-qwen" for i in range(1, 6)], "H-qwen"]
ALL = MAIN + ["A0-qwen", "H-dsflash", "E-qwen", "Q-qwen"]
HARBOR = [sys.executable, "-c", "from harbor.cli.main import app; app()"]


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(RUNTIME), str(REPO)])
    env.pop("MSWEA_API_KEY", None)
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    return env


def prepare() -> None:
    source = Path(next(iter(importlib.util.find_spec("harbor").submodule_search_locations)))
    target = RUNTIME / "harbor"
    if not target.exists():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (RUNTIME / "source.json").write_text(json.dumps({"harbor_source": str(source)}, indent=2))
    subprocess.run([sys.executable, str(REPO / "tua/scripts/patch_harbor.py")], env=environment(), check=True)
    print(f"Isolated Harbor ready: {target}")


def command(config: str, args, batch: Path, names: list[str]) -> list[str]:
    config_path = REPO / "tua/configs" / f"{config}.yaml"
    model = yaml.safe_load(config_path.read_text())["model"]["model_name"]
    cmd = [*HARBOR, "run", "-p", str(args.tasks_dir),
           "--agent-import-path", "tua.local.agent:LocalMini",
           "--ak", f"config_file={config_path}", "--ak", "version=2.4.6", "-m", model,
           "-e", "docker", "-n", str(args.concurrency), "-k", str(args.attempts), "-r", "0",
           "--no-delete", "--agent-setup-timeout-multiplier", "4",
           "-o", str(batch / config), "--job-name", "run", "--yes"]
    if not config.startswith("B"):
        wheels = sorted((REPO / "tua/dist").glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit("Expected one fork wheel. Run: UV_CACHE_DIR=/private/tmp/tua-uv-cache uv build --wheel --out-dir tua/dist")
        cmd += ["--ak", f"fork_wheel={wheels[0]}"]
    for name in names:
        cmd += ["-i", name]
    return cmd


def check(args, names: list[str]) -> None:
    runtime = bundles()
    subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL)
    images = set()
    for name in names:
        task = tomllib.loads((args.tasks_dir / name / "task.toml").read_text())
        image = task["environment"].get("docker_image")
        if not image:
            raise SystemExit(f"No prebuilt image configured for {name}")
        images.add(image)
    for image in sorted(images):
        subprocess.run(["docker", "image", "inspect", image], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "-c", "from tua.local.agent import LocalMini; print('Adapter import OK')"],
                   env=environment(), check=True)
    print(f"Checked {len(names)} tasks, {len(images)} local images, and {len(runtime)} offline runtime checksums. No API requests made.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "runtime-prepare", "runtime-check", "check", "plan", "run", "resume", "summary"])
    parser.add_argument("--tasks-dir", type=Path, default=Path.home() / "TUA-Bench/tasks")
    parser.add_argument("--configs", nargs="+", choices=ALL, default=MAIN)
    parser.add_argument("--parallel", type=int, default=2, help="simultaneous configurations")
    parser.add_argument("--concurrency", type=int, default=1, help="simultaneous trials per configuration")
    parser.add_argument("--attempts", type=int, default=3)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--only", nargs="+", help="selected tasks, must belong to the fixed 40")
    selection.add_argument("--only-file", type=Path, help="JSON selection with a tasks list from the fixed 40")
    parser.add_argument("--batch", type=Path, help="new batch path (run), existing batch path (resume/summary)")
    args = parser.parse_args()
    if args.mode == "runtime-prepare":
        subprocess.run([sys.executable, "-m", "tua.local.prepare_runtime"], cwd=REPO, env=environment(), check=True)
        return
    if args.mode == "runtime-check":
        subprocess.run([sys.executable, "-m", "tua.local.verify_runtime"], cwd=REPO, env=environment(), check=True)
        return
    if min(args.parallel, args.concurrency, args.attempts) < 1:
        parser.error("parallel, concurrency and attempts must be positive")
    if len(args.configs) != len(set(args.configs)):
        parser.error("duplicate configurations")
    subset = json.loads(SUBSET.read_text())["tasks"]
    assert len(subset) == len(set(subset)) == 40
    names = (json.loads(args.only_file.read_text())["tasks"] if args.only_file else
             args.only if args.only is not None else subset)
    if not names:
        parser.error("task selection must not be empty")
    if len(names) != len(set(names)) or not set(names) <= set(subset):
        parser.error("--only must contain unique tasks from the fixed 40")
    args.tasks_dir = args.tasks_dir.expanduser().resolve()
    for name in names:
        if not (args.tasks_dir / name / "task.toml").is_file():
            parser.error(f"missing task: {name}")
    if args.mode == "prepare":
        prepare()
        return
    if args.mode == "check":
        check(args, names)
        return
    if args.mode in {"resume", "summary"} and not args.batch:
        parser.error("--batch is required for resume/summary")
    batch = (args.batch or REPO / "jobs" / f"previous40-{datetime.now():%Y%m%d-%H%M%S}").resolve()
    if args.mode == "summary":
        subprocess.run([sys.executable, str(REPO / "tua/scripts/summarize.py"), str(batch),
                        "--subset", str(args.only_file or SUBSET)], check=True)
        return
    if args.mode == "resume":
        commands = {c: [*HARBOR, "jobs", "resume", "-p", str(batch / c / "run")]
                    for c in args.configs if (batch / c / "run/config.json").exists()}
        if not commands:
            raise SystemExit("No matching jobs found in this batch")
    else:
        commands = {c: command(c, args, batch, names) for c in args.configs}
    print(f"Batch: {batch}\nConfigurations: {len(commands)}; trials/config: {len(names) * args.attempts}; "
          f"maximum active containers: {min(args.parallel, len(commands)) * args.concurrency}", flush=True)
    for c, cmd in commands.items():
        print(f"{c}: PYTHONPATH={shlex.quote(environment()['PYTHONPATH'])} {shlex.join(cmd)}", flush=True)
    if args.mode == "plan":
        return
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("Set OPENROUTER_API_KEY in your terminal before run/resume. No API request made.")
    if args.mode == "run" and batch.exists():
        raise SystemExit("Batch already exists. Choose another --batch or use resume.")
    check(args, names)
    prepare()
    batch.mkdir(parents=True, exist_ok=True)
    if args.mode == "run":
        manifest = {"subset": json.loads(SUBSET.read_text()), "commands": commands,
                    "selected_tasks": names,
                    "selection_file": str(args.only_file.resolve()) if args.only_file else None,
                    "selection_sha256": hashlib.sha256(args.only_file.read_bytes()).hexdigest() if args.only_file else None,
                    "offline_runtime": bundles(),
                    "configs_sha256": {c: hashlib.sha256((REPO / "tua/configs" / f"{c}.yaml").read_bytes()).hexdigest() for c in commands},
                    "wheel_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO / "tua/dist").glob("*.whl")},
                    "parallel": args.parallel, "concurrency": args.concurrency, "attempts": args.attempts,
                    "fork_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()}
        (batch / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    def execute(item: tuple[str, list[str]]) -> int:
        config, cmd = item
        log = batch / f"{config}{'-resume' if args.mode == 'resume' else ''}.log"
        print(f"Starting {config}; log: {log}", flush=True)
        with log.open("a") as output:
            result = subprocess.run(cmd, env=environment(), cwd=REPO, stdout=output, stderr=subprocess.STDOUT)
        print(f"Finished {config}; exit={result.returncode}", flush=True)
        return result.returncode
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        codes = list(pool.map(execute, commands.items()))
    raise SystemExit(1 if any(codes) else 0)


if __name__ == "__main__":
    main()
