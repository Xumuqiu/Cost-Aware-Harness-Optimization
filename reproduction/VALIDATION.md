# Validation of this repository addition

Validated on 2026-11-03 (Asia/Shanghai), without paid model requests or benchmark reruns:

- Built `mini_swe_agent-2.4.6+tua.1-py3-none-any.whl` from the imported source using the locally cached setuptools backend. The wheel includes `TuaAgent`, its helpers and both TUA YAML templates. Generated wheel/build output is ignored by Git.
- Ran `PYTHONPATH=src <existing-development-python> -m pytest tests/agents/test_tua.py tests/config/test_tua_configs.py -q`: **23 passed**. The existing development interpreter was `/Users/xumuqiu/mini-swe-agent/.venv/bin/python`; tests imported this repository's `src/`.
- Checked the raw archive against `results/SHA256SUMS`.
- Extracted the archive and ran `python3 reproduction/recompute.py`: **3,968 evidence hashes and all numeric fields in 440 selected trials verified**, with 40 unique fixed-subset tasks per configuration.
- Generated B0 and B1 stock-Harbor dry-run commands using the published 40-task list; generated A3's fork-Harbor command from the built wheel.
- Generated the recorded-settings replay commands for DS-original and A3 without executing them.
- Generated the local offline-runner plan for B0, B1 and A3 against the existing benchmark task installation. This checks command construction, not container execution.
- Checked local links in the main README, reproduction guide and full report after extracting evidence.
- Scanned imported text and archived logs for credential-shaped values and populated API-key fields. Eight occurrences in six historical log files were redacted; no result JSON was changed.

The benchmark environment's Python did not include pytest. A fresh uv environment could not download build dependencies under the session's restricted DNS, so validation used the existing development environment and cached build backend. A clean networked installation, Docker execution and current model endpoint availability were not tested. These checks do not turn the historical DeepSeek reference into a matched controlled baseline.
