> Historical project note. For portable commands, the published task list, baseline identities and current evidence packaging, use [reproduction/README.md](reproduction/README.md).

# 本机：之前选定的 TUA-Bench 40 题消融实验

准备日期：2026-10-31（Asia/Shanghai）。仓库克隆版本：`3862cb6214186c8e600d85b9447d573f15b7794d`。

## 固定题单与实验设置

使用 `tua/local/subset-previous40.json`，逐项复制自本机 `~/TUA-Bench/configs/terminal40-tasks.txt`，保留原顺序和源文件 SHA-256。**仓库原有 `tua/configs/subset-40.json` 是另一批题，本入口不会使用它，也不会覆盖它。**

| 配置 | 改动 | 模型路由 |
|---|---|---|
| B0-qwen | PyPI mini-swe-agent 2.4.6 基线 | OpenRouter Qwen |
| B1-dsflash | PyPI mini-swe-agent 2.4.6 基线 | OpenRouter DeepSeek |
| A1-qwen | C1 预算可见及配套预算设置 | OpenRouter Qwen |
| A2-qwen | C2 停滞检测及配套恢复/超时设置 | OpenRouter Qwen |
| A3-qwen | C3 提交前自检 | OpenRouter Qwen |
| A4-qwen | C4 观测压缩 | OpenRouter Qwen |
| A5-qwen | C5 任务域提示词 | OpenRouter Qwen |
| H-qwen | C1–C5 全开 | OpenRouter Qwen |
| A0-qwen（可选） | fork 全关 | OpenRouter Qwen |
| H-dsflash（可选） | C1–C5 全开 | OpenRouter DeepSeek |

保留仓库所有模型参数、组件配置和固定价表。Qwen ID 为 `qwen/qwen3.7-flash`；DeepSeek ID 为 `deepseek/deepseek-v4.1-flash-1017`。公开 `/api/v1/models` 查询中两个 ID 均存在；尚未测试账户权限、固定供应商端点或推理请求。

每题重复 3 次是 README 的正式设计，`-k 3` 是独立 trial，不是失败重试；Harbor 失败重试显式设为 0。主实验 8 × 40 × 3 = **960 trials**；只跑 A1–A5 是 600 trials。可用 `--attempts 1` 做初步检查，但所有比较组应保持重复次数一致。

## 环境与已验证内容

- macOS + Docker Desktop，复用 `~/TUA-Bench/tasks` 及该项目的 Python/Harbor 环境，无须重复下载任务。
- 40 题均有现成镜像；各题配置内存 2–4 GiB。Docker 当前总内存约 7.75 GiB（18 CPUs）。**当前建议总并发 1；两组并行前，将 Docker Desktop 内存调到至少 12 GiB，并留意其他容器占用。**
- 总并发上限 = `--parallel`（同时运行几组配置）× `--concurrency`（每组同时运行几个 trial）。默认分别为 2 和 1；不会同时启动所有 8 组。
- wheel 已构建：`tua/dist/mini_swe_agent-2.4.6+tua.1-py3-none-any.whl`。
- 消融相关离线测试 21 passed；10 组命令均验证为固定 40 题、3 次重复、正确的基线/fork 安装来源；真实 Harbor CLI 接受生成的参数；40 个镜像只读检查通过。
- `prepare` 将本机 Harbor 复制到 `tua/local/.runtime/harbor`，仅给该副本应用仓库的日志权限和 oracle helper 删除补丁。原 Harbor 安装未修改。入口显式设置 PYTHONPATH 使用该副本。
- 2026-10-31 安装修复：所有组统一使用容器内 Python venv + 离线 wheel 包；分别覆盖 Python 3.11/3.12 Linux ARM64，每套锁定 93 个依赖并校验 SHA-256。保留 litellm 1.106.6、mcp 2.3.0，固定 datasets 4.5.0，避免旧版依赖回退和源码构建。B0/B1 安装缓存的原版 2.4.6 wheel，其余组上传本 fork wheel。已在禁网任务容器中验证安装与配置运行，不需要每题访问 PyPI。详见 INSTALLATION_REPAIR.md。
- `--no-delete` 在本机 Harbor 中仍清理任务容器及网络，但保留预构建镜像，避免并行组之间删除共用镜像。
- 已修复原汇总脚本误把 job 级 `result.json` 当 trial 的问题，否则可能报 `KeyError: task_name`。
- **准备期间没有发起推理或付费评测，也没有读取、复制或保存任何密钥。**

## 命令

先进入克隆目录：

```bash
cd '/Users/xumuqiu/Desktop/Tri1材料/PE6203/6203_GP_2/mini-swe-agent-tua'
```

在当前终端安全输入 OpenRouter key（zsh 默认；输入不会显示，不写入命令历史或文件）：

```zsh
read -rs 'OPENROUTER_API_KEY?OpenRouter API key: '; echo
export OPENROUTER_API_KEY
```

这里需要 **OpenRouter key**，之前的 DeepSeek 官方 key 不能直接代替。

只读检查与打印命令，不请求模型：

```bash
bash run-previous40.sh check
bash run-previous40.sh plan --parallel 2 --concurrency 1 --attempts 3 --batch jobs/ablation40-main
```

先冒烟验证两种安装来源、自检门和全开配置（3 组 × 1 题 × 1 次，会产生推理费用）：

```bash
caffeinate -i bash run-previous40.sh run \
  --configs B0-qwen A3-qwen H-qwen \
  --only 018-calculate-total-earnings --attempts 1 \
  --parallel 1 --concurrency 1 --batch jobs/smoke40
```

检查 `jobs/smoke40/*.log`、各组 `run/result.json`、trial 的 `agent/setup/local-runtime.txt` 和轨迹。smoke 结果独立保存，不混入主实验。

**完整 8 组，两组并行（先增加 Docker 内存）：**

```bash
caffeinate -i bash run-previous40.sh run \
  --parallel 2 --concurrency 1 --attempts 3 \
  --batch jobs/ablation40-main
```

**只跑五个单组件消融，两组并行：**

```bash
caffeinate -i bash run-previous40.sh run \
  --configs A1-qwen A2-qwen A3-qwen A4-qwen A5-qwen \
  --parallel 2 --concurrency 1 --attempts 3 \
  --batch jobs/ablation40-components
```

如果保持当前 Docker 内存，把上面命令的 `--parallel 2` 改成 `--parallel 1`。

可选对照单独放一个 batch：

```bash
caffeinate -i bash run-previous40.sh run \
  --configs A0-qwen H-dsflash --parallel 1 --concurrency 1 \
  --attempts 3 --batch jobs/ablation40-optional
```

启动器会拒绝覆盖已有 batch；重新开一轮时换一个 `--batch` 名称。若不传 `--batch`，自动使用带时间戳的新目录。

## 日志、续跑、汇总

每组标准输出保存为 `jobs/ablation40-main/<配置名>.log`，Harbor job 位于 `<配置名>/run/`。根目录 `manifest.json` 保存题单、命令、配置和 wheel 哈希及 fork commit，不保存密钥。

```bash
tail -f jobs/ablation40-main/A1-qwen.log

caffeinate -i bash run-previous40.sh resume \
  --batch jobs/ablation40-main --parallel 1

bash run-previous40.sh summary --batch jobs/ablation40-main
```

resume 读取现存 Harbor job 的原配置，继续未完成的 trial；不会按命令行的 attempts/concurrency 改写原 job。`--parallel` 仅控制同时续跑几组。只有已创建 `run/config.json` 的组会被续跑；如果整轮中断时某些组尚未启动，应使用 `run --configs 尚未启动的组 ... --batch 新目录` 启动它们。Harbor resume 对异常 trial 的处理沿用其默认规则；不要选择性重跑低分题。

汇总输出在 `<batch>/summary/`。原脚本的缺失任务警告、平均 reward、完整通过率、异常数均应一起检查；smoke 和正式 batch 分别汇总。多 batch 合并时保持每个配置的独立目录，避免覆盖同名 `run/`。成本是仓库固定价表的离线估算，不是平台实际扣费。

## 与此前成绩的可比性

之前 DeepSeek 40 题是官方直连 `deepseek-flash`、思考 high、100 步/2400 秒、每题 1 次。本 README 实验改用 OpenRouter 的模型 ID 和仓库预算，且统一加入了两处 Harbor 补丁。因此 **旧的 56.60% 平均 reward 不能直接充当本次 B1**；要比较必须在本入口重跑 B1。A1–A5 是“各自单开”消融，不是从 H 逐项删减。

此前报告确认 010/025 有评分参考下载失败、079 有无效 MP3 输入。本次保留原题单和评分规则，没有修复这些资产；正式比较前应检查它们在所有组中的一致性。失败时先看环境/安装/评分日志，不能把所有零分都当成模型失败。

## 维护

本机入口：`run-previous40.sh`、`tua/local/run.py`、`tua/local/agent.py`。详细命令预览已保存到 `tua/local/commands-preview.txt`。重建 wheel：

```bash
UV_CACHE_DIR=/private/tmp/tua-uv-cache uv build --wheel --out-dir tua/dist
bash run-previous40.sh prepare
```

如果改了宿主 Harbor 版本，需要重新创建独立副本并复核补丁。更换 Python 可通过 `TUA_PYTHON=/绝对路径/python bash run-previous40.sh ...` 指定；该环境需要 Harbor、PyYAML 以及原 Harbor 依赖。
