"""Install hash-locked dependencies offline on both supported TUA Python versions."""

import shlex
from pathlib import Path

from harbor.agents.installed.mini_swe_agent import MiniSweAgent
from harbor.environments.base import BaseEnvironment

from tua.local.runtime import BUNDLES, bundles


class LocalMini(MiniSweAgent):
    def __init__(self, fork_wheel: str | None = None, **kwargs):
        self.wheel = Path(fork_wheel).resolve() if fork_wheel else None
        self.runtime = bundles()
        super().__init__(**kwargs)

    def get_version_command(self) -> str:
        return '. "$HOME/.local/bin/env"; python -c \'from importlib.metadata import version; print(version("mini-swe-agent"))\''

    async def install(self, environment: BaseEnvironment) -> None:
        detected = await self.exec_as_agent(environment, command=(
            "python3 -c 'import sys,platform; "
            'print("py%d%d-%s" % (*sys.version_info[:2], platform.machine()))' + "'"
        ))
        key = detected.stdout.strip()
        if key not in self.runtime:
            raise ValueError(f"No offline runtime for {key}; supported: {list(self.runtime)}")
        entry = self.runtime[key]
        source = BUNDLES / entry["archive"]
        target = f"/tmp/{source.name}"
        await environment.upload_file(source, target)
        await self.exec_as_root(environment, command=f"chmod 644 {shlex.quote(target)}")
        spec = f'/tmp/tua-offline-runtime/{entry["baseline_wheel"]}'
        if self.wheel:
            spec = f"/tmp/{self.wheel.name}"
            await environment.upload_file(self.wheel, spec)
            await self.exec_as_root(environment, command=f"chmod 644 {shlex.quote(spec)}")
        await self.exec_as_agent(
            environment,
            command=(
                'set -euo pipefail; mkdir -p "$HOME/.local/bin" /logs/agent/setup; '
                f"echo '{entry['sha256']}  {target}' | sha256sum -c -; "
                'mkdir -p /tmp/tua-offline-runtime; '
                f'tar -xf {shlex.quote(target)} -C /tmp/tua-offline-runtime; '
                'python3 -m venv "$HOME/.local/share/mini-swe-agent"; '
                '{ "$HOME/.local/share/mini-swe-agent/bin/pip" --isolated install '
                '--no-index --only-binary=:all: --find-links /tmp/tua-offline-runtime '
                '--require-hashes -r /tmp/tua-offline-runtime/requirements.txt; '
                '"$HOME/.local/share/mini-swe-agent/bin/pip" --isolated install '
                f'--no-index --no-deps {shlex.quote(spec)}; '
                '"$HOME/.local/share/mini-swe-agent/bin/pip" check; } '
                '2>&1 | tee /logs/agent/setup/local-runtime.txt; '
                "printf 'export PATH=\"%s/.local/share/mini-swe-agent/bin:$PATH\"\\n' \"$HOME\" "
                '> "$HOME/.local/bin/env"; '
                'source "$HOME/.local/bin/env"; LITELLM_LOCAL_MODEL_COST_MAP=True mini-swe-agent --help'
            ),
        )
