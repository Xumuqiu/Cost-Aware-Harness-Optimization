# Cost-Aware Harness Optimization

A mini-swe-agent fork for studying task success versus inference cost on **TUA-Bench**, using its official Harbor runner and task verifiers. The low-cost model stays fixed while five independently configurable harness components change the execution loop.

## Codebase deliverables

| Requirement | Implementation |
|---|---|
| Harness under our control | Full fork source in [`src/minisweagent`](src/minisweagent), based on mini-swe-agent 2.4.6; [MIT attribution](LICENSE.md) and [provenance](reproduction/provenance.json) |
| Official benchmark integration | [`tua/harbor_agent.py`](tua/harbor_agent.py), [`tua/local/agent.py`](tua/local/agent.py), and [shared runner patches](tua/scripts/patch_harbor.py); official TUA-Bench tasks/verifiers |
| Improved harness | [`TuaAgent`](src/minisweagent/agents/tua.py), [helpers](src/minisweagent/agents/utils/tua_utils.py), and [task-domain prompt](src/minisweagent/config/tua/prompt_tua.yaml); A1–A5 ablations and H/E/Q combinations |
| Default-harness baseline | [`B0-qwen.yaml`](tua/configs/B0-qwen.yaml): stock PyPI mini-swe-agent 2.4.6, default harness settings, same Qwen model. A0 is the fork with all components off; offline tests check parity on deterministic trajectories |
| Expensive-model baseline | [`B1-dsflash.yaml`](tua/configs/B1-dsflash.yaml): stock harness with the project's higher-price DeepSeek configuration. Archived `DS-original` is a historical DeepSeek reference, with its actual settings separately preserved |
| Reproduction material | [Setup and commands](reproduction/README.md), [recorded effective configurations](reproduction), [440-trial index](results/trials.csv), [raw logs](results/raw-440.tar.gz), [checksums](results/evidence-manifest.json), and [offline recomputation](reproduction/recompute.py) |

## Improvements

| Component | Mechanism | Configuration |
|---|---|---|
| C1: budget visibility | Step/time notices and a wrap-up reminder | A1 |
| C2: stall recovery | Repeated-command/output detection and timeout/format-error recovery | A2 |
| C3: pre-submission verification | Intercept the first submission, inspect file structure and spreadsheet formula caches, return feedback | A3 |
| C4: observation compression | Remove common noise and compact older tool observations while retaining full trajectories | A4 |
| C5: task-domain prompts | General workflow for terminal, Office and browser tasks; no task-specific solutions | A5 |

H enables all five; E enables C1+C2+C4; Q enables C1+C2+C3+C5. These are execution and prompting changes; the added hooks do not call a separate LLM. They can cause additional calls to the base model.

## Recorded results

One selected trial per task on a fixed, manually selected 40-task subset. Cost is a standardized estimate from recorded usage and the project's archived price table, not an invoice.

| Configuration | Full passes | Mean reward | Estimated USD/task |
|---|---:|---:|---:|
| A0: Qwen, all components off | 7/40 | 0.2317 | 0.006548 |
| A2: Qwen + C2 | 10/40 | 0.2957 | 0.004590 |
| A3: Qwen + C3 | 14/40 | 0.4138 | 0.007444 |
| DS-original: historical stock DeepSeek | 20/40 | 0.5660 | 0.014074 |

**Baseline distinction:** A0 is the primary same-model ablation control. The recorded historical stock Qwen run (`B0-hist`) used different reasoning/budget settings. The historical DeepSeek run used the official `deepseek-flash` API alias, high reasoning and a 100-step/2400-second budget; its exact weights cannot be established from the alias. It must not be relabeled as a completed run of the planned `B1-dsflash.yaml` OpenRouter configuration. A controlled stronger-model comparison with matched routing, reasoning and environment remains future work. Historical success rates do not independently establish intrinsic model strength.

A0–A2 use the second of three historical repetitions, selected after inspecting infrastructure failures. A3–A5 use a later completed recovery batch. H combines 21 original trials with 19 installation-repair trials. Missing rewards count as zero in the fixed denominator. These choices and environment differences limit causal and statistical conclusions. See the [full report](reports/report.md).

## Recompute without model calls

Requires Python 3.11+; this path uses the standard library only.

```bash
(cd results && shasum -a 256 -c SHA256SUMS)
tar -xzf results/raw-440.tar.gz
python3 reproduction/recompute.py
```

The script checks every evidence hash, all trial metrics (including the report's approximate overhead allocation), and one record per task per group. Raw evidence is compressed for GitHub; after extraction, `results/raw/` holds results, configurations, trajectories, agent/setup output, verifier logs and exceptions. Generated task artifacts and Docker images are not included.

## Run experiments

Follow the [reproduction guide](reproduction/README.md) to pin TUA-Bench and Harbor, build the fork, prepare the offline dependency bundles and print/run the baseline and variant commands. Paid benchmark runs are separate from offline verification.

## Attribution

Based on [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) and the project fork [zhaoyijie1201/mini-swe-agent-tua](https://github.com/zhaoyijie1201/mini-swe-agent-tua). Benchmark: [facebookresearch/TUA-Bench](https://github.com/facebookresearch/TUA-Bench). Original license notices are preserved in [LICENSE.md](LICENSE.md); the repository's existing [LICENSE](LICENSE) is retained.
