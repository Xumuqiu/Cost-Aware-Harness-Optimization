"""Exercise the real Harbor installer in network-disabled disposable task containers."""

import asyncio
import json
import shlex
import time
import tomllib
from datetime import datetime
from pathlib import Path

from harbor.environments.docker.docker import DockerEnvironment
from harbor.models.task.config import TaskConfig
from harbor.models.trial.paths import TrialPaths

from tua.local.agent import LocalMini

REPO = Path(__file__).resolve().parents[2]
PROBE = '''
import importlib.metadata as M
import json
import sys
from pathlib import Path
import datasets, litellm, mcp, pyarrow
import yaml
from minisweagent.agents import get_agent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.test_models import DeterministicToolcallModel, make_toolcall_output

for name in ['E-qwen', 'Q-qwen', 'H-qwen']:
    config = yaml.safe_load(Path('/tmp/' + name + '.yaml').read_text())
    outputs = []
    for i, command in enumerate(['echo offline-probe', 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT', 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT']):
        outputs.append(make_toolcall_output(None, [{'id': str(i), 'type': 'function', 'function': {'name': 'bash', 'arguments': json.dumps({'command': command})}}], [{'command': command, 'tool_call_id': str(i)}]))
    agent = get_agent(DeterministicToolcallModel(outputs=outputs), LocalEnvironment(**config['environment']), config['agent'] | {'mode': 'yolo', 'confirm_exit': False, 'cost_limit': 0}, default_type='interactive')
    assert agent.run('Run the offline installation probe')['exit_status'] == 'Submitted'
print('OFFLINE_PROBE_OK', sys.version.split()[0], {name: M.version(name) for name in ['mini-swe-agent', 'litellm', 'mcp', 'datasets', 'pyarrow']})
'''


async def main() -> None:
    root = REPO / "tua/local/.runtime" / f"validation-{datetime.now():%Y%m%d-%H%M%S}"
    results = []
    cases = [("018-calculate-total-earnings", True), ("102-daily-email-report", True),
             ("018-calculate-total-earnings", False)]
    for index, (name, fork) in enumerate(cases):
        task = Path.home() / "TUA-Bench/tasks" / name
        config = TaskConfig.model_validate(tomllib.loads((task / "task.toml").read_text()))
        config.environment.allow_internet = False
        paths = TrialPaths(root / f"{name}-{'fork' if fork else 'baseline'}")
        paths.mkdir()
        env = DockerEnvironment(environment_dir=task / "environment", environment_name=name,
                                session_id=f"tua-offline-check-{int(time.time())}-{index}", trial_paths=paths,
                                task_env_config=config.environment)
        env.default_user = "agent"
        agent = LocalMini(logs_dir=paths.agent_dir, fork_wheel=str(next((REPO / "tua/dist").glob("*.whl"))) if fork else None,
                          model_name="openrouter/qwen/qwen3.7-flash", version="2.4.6")
        start = time.monotonic()
        try:
            await env.start(force_build=False)
            await agent.install(env)
            if fork:
                for config_name in ["E-qwen", "Q-qwen", "H-qwen"]:
                    await env.upload_file(REPO / f"tua/configs/{config_name}.yaml", f"/tmp/{config_name}.yaml")
                command = '. "$HOME/.local/bin/env"; LITELLM_LOCAL_MODEL_COST_MAP=True python -c ' + shlex.quote(PROBE)
            else:
                command = '. "$HOME/.local/bin/env"; python -c \'from importlib.metadata import version; assert version("mini-swe-agent")=="2.4.6"; print("BASELINE_OK")\''
            probe = await agent.exec_as_agent(env, command=command)
            print(probe.stdout[-1800:], flush=True)
            version = await agent.exec_as_agent(env, command=agent.get_version_command())
            results.append({"task": name, "fork": fork, "network": "disabled", "version": version.stdout.strip(),
                            "seconds": round(time.monotonic() - start, 2), "status": "passed"})
            (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        finally:
            await env.stop(delete=False)
    print(f"All offline installation checks passed: {root / 'results.json'}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
