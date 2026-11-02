"""Download wheels on the host once, then publish versioned offline bundles."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from packaging.utils import parse_wheel_filename

from tua.local.runtime import BUNDLES, bundles, digest

LOCAL = Path(__file__).resolve().parent
REPO = LOCAL.parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true", help="package previously downloaded wheel directories")
    args = parser.parse_args()
    if not args.cached and (BUNDLES / "manifest.json").exists():
        bundles()
        print("Existing offline runtime bundles passed checksum validation; no downloads needed.")
        return
    tool_dir = LOCAL / ".runtime/download-tools"
    env = os.environ | {"PYTHONPATH": str(tool_dir), "UV_CACHE_DIR": "/private/tmp/tua-uv-cache"}
    if not args.cached:
        subprocess.run(["uv", "pip", "install", "--target", str(tool_dir), "pip==26.2.2"], env=env, check=True)
    pip = [sys.executable, "-m", "pip", "--isolated", "download", "--index-url", "https://pypi.org/simple",
           "--timeout", "45", "--retries", "5"]
    wheels = list((REPO / "tua/dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected one fork wheel in tua/dist")
    BUNDLES.mkdir(parents=True, exist_ok=True)
    locks = LOCAL / "locks"
    locks.mkdir(exist_ok=True)
    manifest = {}
    for version in ["311", "312"]:
        directory = LOCAL / f".runtime/wheels-cp{version}"
        if not args.cached:
            saved_lock = locks / f"py{version}-aarch64.txt"
            requirements = (["--require-hashes", "-r", str(saved_lock)] if saved_lock.exists() else
                            [str(wheels[0]), "litellm==1.106.6", "mcp==2.3.0", "datasets==4.5.0"])
            subprocess.run([*pip, "--only-binary=:all:", "--platform", "manylinux_2_28_aarch64",
                            "--platform", "manylinux2014_aarch64", "--platform", "manylinux_2_17_aarch64",
                            "--implementation", "cp", "--python-version", f"3.{version[1:]}",
                            "--abi", f"cp{version}", "--dest", str(directory), *requirements], env=env, check=True)
            shutil.copy2(wheels[0], directory / wheels[0].name)
            subprocess.run([*pip, "--only-binary=:all:", "--no-deps", "--dest", str(directory),
                            "mini-swe-agent==2.4.6"], env=env, check=True)
        if not directory.exists():
            raise FileNotFoundError(directory)
        packages = {}
        requirements = []
        for path in sorted(directory.glob("*.whl")):
            name, package_version, _, _ = parse_wheel_filename(path.name)
            if name == "mini-swe-agent":
                continue
            if name in packages:
                raise ValueError(f"Multiple wheels for {name}; use a clean wheel directory")
            packages[name] = str(package_version)
            requirements.append(f"{name}=={package_version} --hash=sha256:{digest(path)}")
        assert packages["litellm"] == "1.106.6" and packages["mcp"] == "2.3.0" and packages["datasets"] == "4.5.0"
        lock = "\n".join(sorted(requirements)) + "\n"
        (directory / "requirements.txt").write_text(lock)
        (locks / f"py{version}-aarch64.txt").write_text(lock)
        key = f"py{version}-aarch64"
        temporary = BUNDLES / f".{key}.tar.tmp"
        with tarfile.open(temporary, "w") as archive:
            for path in sorted(directory.iterdir()):
                if path.suffix == ".whl" or path.name == "requirements.txt":
                    archive.add(path, arcname=path.name)
        checksum = digest(temporary)
        target = BUNDLES / f"{key}-{checksum[:16]}.tar"
        temporary.replace(target)
        baseline = directory / "mini_swe_agent-2.4.6-py3-none-any.whl"
        if not baseline.exists():
            raise FileNotFoundError("Baseline wheel missing; rerun without --cached")
        manifest[key] = {"archive": target.name, "sha256": checksum, "packages": packages,
                         "baseline_wheel": baseline.name, "baseline_sha256": digest(baseline),
                         "lock_sha256": digest(directory / "requirements.txt")}
        print(f"Prepared {key}: {len(packages)} locked dependencies, {target.stat().st_size / 1e6:.1f} MB", flush=True)
    temporary = BUNDLES / ".manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(BUNDLES / "manifest.json")
    shutil.copy2(BUNDLES / "manifest.json", locks / "manifest.json")


if __name__ == "__main__":
    main()
