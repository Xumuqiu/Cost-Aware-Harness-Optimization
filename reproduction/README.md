# Reproduction guide

## 1. Offline audit of the published results

From the repository root:

```bash
(cd results && shasum -a 256 -c SHA256SUMS)
tar -xzf results/raw-440.tar.gz
python3 reproduction/recompute.py
```

Python 3.11+ is sufficient; this does not import LiteLLM or call any service. `results/trials.csv` selects exactly 440 trials: 40 each for A0–A5, DS-original, B0-hist, E, Q and H. The audit verifies 3,968 evidence-file hashes, original result hashes, reward, token usage, estimated total cost, and the report's approximate harness cost allocation. It writes `results/recomputed-summary.csv`.

The raw archive retains each selected trial's `result.json`, `config.json`, agent trajectories/text, setup output, verifier logs, trial log and exception text when present. It excludes `artifacts/`, images and task assets. Eight credential-shaped occurrences were replaced by `[REDACTED_CREDENTIAL]` before publication. Per-file hashes describe the published bytes; all 440 `result.json` files are unchanged and retain their original hashes. Redacted files are marked in `results/evidence-manifest.json`. Paths inside original logs are historical metadata and may refer to the original machine; index paths are portable.

The effective configuration recorded in the first available trajectory of each group is exported as `*.recorded-config.json`. Each trial's own configuration remains authoritative. `DS-original.recorded-config.json` preserves the actual direct-API alias and reasoning settings. Generated YAML configurations under `tua/configs/` describe the planned experiment matrix; they are not evidence that every configuration has been run.

## 2. Environment and official benchmark

Use Python 3.12, uv, Docker and enough memory for the selected task containers. The historical offline bundles target **Linux aarch64, Python 3.11/3.12** inside Docker. An x86_64 host needs separately prepared dependency locks/bundles or the online stock runner described below; do not use aarch64 wheels on x86_64.

```bash
git clone https://github.com/Xumuqiu/Cost-Aware-Harness-Optimization.git
cd Cost-Aware-Harness-Optimization
git clone https://github.com/facebookresearch/TUA-Bench.git ../TUA-Bench
git -C ../TUA-Bench checkout 3497fd320abcafaf4797424192c891a593fd7964
(cd ../TUA-Bench && uv sync && uv run setup-env)
# The project runner requires Harbor 0.6.3; check before patching/running.
uv run --project ../TUA-Bench python -c 'from importlib.metadata import version; assert version("harbor")=="0.6.3"'
uv build --wheel --out-dir tua/dist
export TUA_PYTHON="$(cd ../TUA-Bench && pwd)/.venv/bin/python"
```

The exact reported task list is [`tua/local/subset-previous40.json`](../tua/local/subset-previous40.json). `tua/configs/subset-40.json` is a different, stratified list from the initial proposal; do not substitute it when reproducing these results. Obtain benchmark assets with the official setup workflow; this repository does not redistribute them.

## 3. Shared installation and runner fixes (historical aarch64 route)

```bash
bash run-previous40.sh runtime-prepare --tasks-dir ../TUA-Bench/tasks
bash run-previous40.sh runtime-check --tasks-dir ../TUA-Bench/tasks
bash run-previous40.sh prepare --tasks-dir ../TUA-Bench/tasks
bash run-previous40.sh check --tasks-dir ../TUA-Bench/tasks
```

`runtime-prepare` downloads dependency wheels on the host using the hash-locked requirements in `tua/local/locks/`, then packages them for offline task-container installation. The fork wheel and stock PyPI 2.4.6 wheel are separate. `tua.local.agent:LocalMini` installs the stock wheel for B configurations and the fork for A/H/E/Q; it inherits Harbor's execution and scoring interface. The offline runtime, wheel downloads and images are intentionally not checked into Git.

`prepare` copies Harbor into an isolated local runtime and applies shared patches: correct log/artifact permissions under the non-root task user and remove the image's `chrome_state.py` answer shortcut. Tasks and official verifier logic are unchanged. Both baselines and variants use these same runner patches. See [`patch_harbor.py`](../tua/scripts/patch_harbor.py). Do not compare patched and unpatched execution without disclosing the environment difference.

## 4. Default baseline, higher-price baseline and variants

Set `OPENROUTER_API_KEY` in your terminal using your own secret-management method. The following plan command only prints commands; `run` invokes the API and incurs charges.

```bash
bash run-previous40.sh plan --tasks-dir ../TUA-Bench/tasks \
  --configs B0-qwen B1-dsflash A0-qwen A1-qwen A2-qwen A3-qwen A4-qwen A5-qwen H-qwen \
  --parallel 1 --concurrency 1 --attempts 1

bash run-previous40.sh run --tasks-dir ../TUA-Bench/tasks \
  --configs B0-qwen B1-dsflash A0-qwen A1-qwen A2-qwen A3-qwen A4-qwen A5-qwen H-qwen \
  --parallel 1 --concurrency 1 --attempts 1 --batch jobs/reproduction-01
```

B0 uses stock mini-swe-agent 2.4.6 with default harness settings and Qwen, matching the variants' base model and provider settings. B1 uses stock mini-swe-agent with the project's higher-price DeepSeek OpenRouter configuration. The archived price snapshot lists higher non-cached input/output rates, but **actual cost per run must be measured**; higher rates alone do not ensure a higher total. Provider aliases and endpoint availability can change. A new B1 run is needed to assess its quality and comparable/higher cost against the same current task environment. This repository supplies the configuration and historical evidence, and does not claim that this matched experiment is completed.

For more repetitions, choose `--attempts 3` before running and report all repetitions, with a predeclared treatment of infrastructure failures. Never select the highest score per task.

```bash
bash run-previous40.sh resume --tasks-dir ../TUA-Bench/tasks \
  --configs B0-qwen B1-dsflash A0-qwen A1-qwen A2-qwen A3-qwen A4-qwen A5-qwen H-qwen \
  --parallel 1 --batch jobs/reproduction-01
bash run-previous40.sh summary --tasks-dir ../TUA-Bench/tasks --batch jobs/reproduction-01
```

For a network-enabled Linux task environment, the simpler stock Harbor route also exists. Use the **published** task list explicitly:

```bash
(cd ../TUA-Bench && uv run python ../Cost-Aware-Harness-Optimization/tua/scripts/patch_harbor.py)
python3 tua/scripts/run_config.py B0-qwen --tasks-dir ../TUA-Bench/tasks \
  --subset tua/local/subset-previous40.json --harbor 'uv run --project ../TUA-Bench harbor' --dry-run
python3 tua/scripts/run_config.py B1-dsflash --tasks-dir ../TUA-Bench/tasks \
  --subset tua/local/subset-previous40.json --harbor 'uv run --project ../TUA-Bench harbor' --dry-run
python3 tua/scripts/run_config.py A3-qwen --tasks-dir ../TUA-Bench/tasks \
  --subset tua/local/subset-previous40.json --harbor 'uv run --project ../TUA-Bench harbor' --dry-run
```

Remove `--dry-run` only when ready to run. This alternate route downloads dependencies inside containers and is not the repaired offline environment used for the later historical batches.

### Replay archived effective settings

[`configs/`](configs/) contains runnable YAML equivalents of the recorded effective settings (JSON syntax is valid YAML). Runtime type identifiers are mapped to `agent_class`, `model_class` and `environment_class`, and the old output path is removed. The original `*.recorded-config.json` snapshots are retained separately.

```bash
python3 reproduction/replay_recorded.py DS-original --tasks-dir ../TUA-Bench/tasks \
  --harbor 'uv run --project ../TUA-Bench harbor'
python3 reproduction/replay_recorded.py A3 --tasks-dir ../TUA-Bench/tasks \
  --harbor 'uv run --project ../TUA-Bench harbor'
```

These commands only print a full 40-task Harbor command. Add `--run` to execute after setting the relevant provider key. They use the online stock/fork installer and the archived agent/model settings; they cannot recreate a historical provider, cache state, patched runtime or model alias weights. Apply the shared runner patches first. Use the per-trial recorded settings when auditing any differences within a group.

## 5. Historical selection and comparison limits

- A0–A2: second chronological repetition per task, chosen retrospectively after comparing infrastructure failures; 40 trials per configuration. Other historical repetitions are outside this release's reported sample.
- A3–A5: later completed single-run recovery batch, including resumed trials.
- H: 21 original trials plus 19 replacement trials after fixing installation; original failed installation trials are not counted twice.
- B0-hist: stock Qwen, high reasoning, 100-step/2400-second limits. It differs from the planned default-settings B0 and the A0 control.
- DS-original: stock mini-swe-agent using `deepseek/deepseek-flash` through `https://api.deepseek.com`, thinking enabled, reasoning effort high, max output 16,384 tokens, 100 steps and 2400 seconds. The alias does not identify fixed weights. A rerun would need a `DEEPSEEK_API_KEY` passed through the official adapter and the recorded configuration; the OpenRouter B1 command above does not replay this historical run.

All groups use the full 40-task denominator; missing rewards count as zero. Report full-pass rate separately from mean reward. Cost uses the archived 2026-10-30 table in `tua/pricing/prices.json`, applied to the response usage with cache input counted once. The DeepSeek price tier is a normalization assumption for the historical alias, not its verified invoice. Harness overhead uses the published character-based approximation; it is not precise per-component billing. Machine cost and failed requests without usage are excluded.

The original Chinese documents under `tua/` and the root are historical project notes; this guide supersedes their machine-specific commands, initial task-list choice and planned repeat counts for the published sample.

## 6. Offline code tests

With the benchmark Python environment containing the project's development dependencies:

```bash
PYTHONPATH=src "$TUA_PYTHON" -m pytest tests/agents/test_tua.py tests/config/test_tua_configs.py -q
```

These deterministic tests exercise all-off parity, recovery, submission interception, output handling, prompt rendering and the baseline/configuration matrix. They do not call paid models or execute the official benchmark. See `VALIDATION.md` for the checks performed for this repository addition.
