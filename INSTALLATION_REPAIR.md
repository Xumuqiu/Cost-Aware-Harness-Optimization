> Historical project note. For portable commands, the published task list, baseline identities and current evidence packaging, use [reproduction/README.md](reproduction/README.md).

# 依赖安装修复记录

修复日期：2026-10-31（Asia/Shanghai）。本次修复针对 H-qwen 上一轮 19 个 agent 安装异常，没有修改任务、评分器、模型路由或 C1–C5 实现，也没有启动付费模型评测。

## 问题与修复

旧安装器在每个任务容器中访问 PyPI 并重新解析全部依赖。此前 18 个安装异常日志含 SSL/TLS 错误，另 1 个在 pip 解析索引时触发 JSONDecodeError。102 任务还回退至 datasets 1.8.0、pyarrow 3.0.0 的源码构建链路。

新安装器先在宿主机准备离线 wheel 包，再上传到任务容器：

- 分别准备 Linux ARM64 Python 3.11 和 3.12 两套运行依赖。
- 每套 93 个依赖均锁定精确版本和 wheel SHA-256；保留 litellm 1.106.6、mcp 2.3.0，固定 datasets 4.5.0。全部使用二进制 wheel，不在任务中构建源码。
- 宿主机检查整个离线包校验值，上传后容器再次验证归档 SHA-256；pip 使用 `--isolated --no-index --require-hashes` 安装依赖。
- fork wheel 单独上传，使用 `--no-index --no-deps` 安装；基线使用离线包中的 PyPI 原版 2.4.6 wheel。
- 安装后执行 pip check 和 mini-swe-agent --help，提前暴露缺依赖或不兼容问题。
- 修复版本检测命令：从当前 venv 读取 mini-swe-agent 的实际版本，不再调用未安装的 uv tool list。
- 缺少运行包、校验值不匹配或 Python/架构不受支持时直接报错，不静默回退到联网安装。
- 新 Job 的 manifest.json 记录完整离线运行包版本、依赖版本和哈希，便于对照。

依赖包在 `tua/local/.runtime/bundles/`，合计约 327 MB；属于本机缓存，不提交 Git。精确版本锁和哈希记录保存在 `tua/local/locks/`。两套包除了 numpy 版本因 Python 目标不同而分别为 2.4.6 和 2.5.4，其余依赖版本一致；同一任务的所有实验组使用同一套包。

## 验证结果

对固定题单全部 40 个镜像执行禁网的轻量 Python 探测，得到 Python 3.11 ARM64 共 20 个、Python 3.12 ARM64 共 20 个，均被离线包覆盖。

使用真实 Harbor DockerEnvironment 和真实 LocalMini.install，在禁止网络访问的一次性任务容器中验证：

| 镜像对应任务 | 安装版本 | 结果 | 环境启动、安装与检查合计 |
|---|---|---|---:|
| 018-calculate-total-earnings，Python 3.12 | fork 2.4.6+tua.1 | 通过 | 19.35 秒 |
| 102-daily-email-report，Python 3.11 | fork 2.4.6+tua.1 | 通过 | 16.78 秒 |
| 018-calculate-total-earnings，Python 3.12 | 原版 2.4.6 | 通过 | 17.15 秒 |

两种 Python 环境中的 fork 都实际导入 datasets、pyarrow、litellm、mcp，并使用确定性工具响应验证 E-qwen、Q-qwen、H-qwen 的运行与提交流程。此检查不请求模型，不产生推理费用；基线版本也完成安装和版本校验。没有在 40 个镜像中逐一执行完整安装或正式任务评测。

现有消融及配置离线测试：23 passed。测试容器、网络已清理，原有镜像保留。

原始验证记录：

- `tua/local/.runtime/validation-20261031-171137/results.json`
- `tua/local/.runtime/offline-validation.log`
- `tua/local/.runtime/image-runtime-inventory.json`

## 继续运行两组组合实验

当前终端设置 OPENROUTER_API_KEY 后，原来的命令直接使用新安装器：

```bash
cd '/Users/xumuqiu/Desktop/Tri1材料/PE6203/6203_GP_2/mini-swe-agent-tua'
caffeinate -i bash run-previous40.sh run \
  --configs E-qwen Q-qwen \
  --parallel 2 --concurrency 1 --attempts 1
```

每组 40 题、每题一次，合计 80 个 trial，同时最多两个任务容器。建议 Docker Desktop 至少分配 12 GiB 内存。当前修复没有调整 Docker 内存设置。

离线包已准备完成，无须重复下载。只读校验：

```bash
bash run-previous40.sh check
```

重新执行禁网安装与配置验证（启动临时容器，不调用模型）：

```bash
bash run-previous40.sh runtime-check
```

缓存被移除后可重新准备；宿主机需要联网，已有版本锁会用于依赖下载：

```bash
bash run-previous40.sh runtime-prepare
```

已有缓存完整时，上述命令只校验并复用，不重新下载。

## 对后续结果的影响

这次消除了 agent 安装步骤对任务容器实时访问 PyPI 的需求。模型 API、任务本身下载素材、verifier 下载参考文件等步骤仍可能有网络问题，本次没有验证或修复这些其他链路。

安装方式和传递依赖已统一锁定，旧 H-qwen 的历史 12.50% 结果仍保留原样。新两组可以在相同修复环境下比较；不能将新结果与旧结果的差异全部归因于 C1–C5 开关。若需要严格比较全开 H-qwen，应在修复后的环境另建 Job 运行。
