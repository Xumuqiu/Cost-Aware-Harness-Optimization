"""Print or run official Harbor commands using a group's archived effective settings."""
import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = Path(__file__).resolve().parent / 'configs'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('group', choices=sorted(p.stem for p in CONFIGS.glob('*.yaml')))
    parser.add_argument('--tasks-dir', type=Path, required=True)
    parser.add_argument('--harbor', default='harbor')
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--jobs-dir', type=Path, default=Path('jobs/recorded-replays'))
    parser.add_argument('--run', action='store_true', help='execute a paid run; default only prints the command')
    args = parser.parse_args()
    config = CONFIGS / f'{args.group}.yaml'
    data = json.loads(config.read_text())
    model = data['model']['model_name']
    cmd = [*shlex.split(args.harbor), 'run', '-p', str(args.tasks_dir.resolve())]
    for task in json.loads((ROOT / 'tua/local/subset-previous40.json').read_text())['tasks']:
        cmd += ['-i', task]
    if args.group in ['DS-original', 'B0-hist']:
        cmd += ['-a', 'mini-swe-agent', '--ak', 'version=2.4.6']
    else:
        wheels = list((ROOT / 'tua/dist').glob('*.whl'))
        if args.wheel is None and len(wheels) != 1:
            parser.error('build exactly one fork wheel in tua/dist or provide --wheel')
        wheel = args.wheel or wheels[0]
        cmd += ['--agent-import-path', 'tua.harbor_agent:MiniSweAgentFork', '--ak', f'fork_wheel={wheel.resolve()}']
    cmd += ['--ak', f'config_file={config}', '-m', model, '-e', 'docker', '-n', '1', '-k', '1',
            '-r', '0', '-o', str(args.jobs_dir / args.group), '--yes']
    env = os.environ | {'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    print('PYTHONPATH=' + shlex.quote(env['PYTHONPATH']), shlex.join(cmd), flush=True)
    if args.run:
        key = 'DEEPSEEK_API_KEY' if args.group == 'DS-original' else 'OPENROUTER_API_KEY'
        if not env.get(key):
            parser.error(f'set {key} before running; no API request made')
        raise SystemExit(subprocess.call(cmd, cwd=ROOT, env=env))


if __name__ == '__main__':
    main()
