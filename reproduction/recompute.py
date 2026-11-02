"""Verify archived evidence and reproduce all 440 selected trial metrics without an API."""
import csv
import hashlib
import json
import math
from pathlib import Path

import accounting

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    records = list(csv.DictReader((ROOT / 'results/trials.csv').open(encoding='utf-8')))
    tasks = set(json.loads((ROOT / 'tua/local/subset-previous40.json').read_text())['tasks'])
    manifest = json.loads((ROOT / 'results/evidence-manifest.json').read_text())
    for item in manifest:
        path = ROOT / item['path']
        if not path.exists():
            raise SystemExit('Extract evidence first: tar -xzf results/raw-440.tar.gz')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise SystemExit(f'Checksum mismatch: {path}')
    for row in records:
        if row['config'] == 'A0':
            trajectory = json.loads((ROOT / row['trajectory_path']).read_text())
            accounting.base_initial[row['task']] = sum(len(accounting.text(m)) for m in trajectory['messages'][:2])
    numbers = ['reward', 'input_tokens', 'cached_tokens', 'output_tokens', 'calls', 'fixed_cost_usd',
               'harness_tokens_est', 'harness_cost_est', 'harness_cost_low', 'harness_cost_high',
               'inference_tokens_residual', 'inference_cost_residual']
    actual = []
    for row in records:
        path = ROOT / row['result_path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise SystemExit(f'Result differs from published index: {path}')
        measured = accounting.parse(path, row['config'], row['source'])
        if measured['task'] != row['task']:
            raise SystemExit(f'Task mismatch: {path}')
        for key in numbers:
            if not math.isclose(float(row[key]), measured[key], rel_tol=1e-10, abs_tol=1e-10):
                raise SystemExit(f'{path}: {key}: expected {row[key]}, got {measured[key]}')
        actual.append(measured)
    summary = []
    for config in dict.fromkeys(r['config'] for r in actual):
        group = [r for r in actual if r['config'] == config]
        if len(group) != 40 or {r['task'] for r in group} != tasks:
            raise SystemExit(f'{config}: expected one trial for each fixed task')
        summary.append(dict(config=config, trials=len(group), full_passes=sum(r['full_pass'] for r in group),
                            success_rate=sum(r['full_pass'] for r in group)/40,
                            mean_reward=sum(r['reward'] for r in group)/40,
                            usd_per_task=sum(r['fixed_cost_usd'] for r in group)/40,
                            total_usd=sum(r['fixed_cost_usd'] for r in group)))
    target = ROOT / 'results/recomputed-summary.csv'
    with target.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    print(f'Verified {len(manifest)} evidence files and all numeric fields in {len(actual)} trials.')
    for row in summary:
        print(f"{row['config']:12s} {row['full_passes']:2d}/40  reward={row['mean_reward']:.4f}  USD/task={row['usd_per_task']:.6f}")
    print(f'Wrote {target.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
