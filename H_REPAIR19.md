> Historical project note. For portable commands, the published task list, baseline identities and current evidence packaging, use [reproduction/README.md](reproduction/README.md).

# H-qwen：仅补跑上次安装失败的 19 题

来源为 `jobs/previous40-20261031-130932/H-qwen/run`，Job ID 为 b0a06491-0f6c-4f9d-8902-1d2aa884bd4f。

核查 40 个 trial 后，19 个同时满足：存在 NonZeroAgentExitCodeError、agent_execution 未开始、没有 verifier reward，安装日志包含 SSL/TLS 下载错误或 pip 索引 JSONDecodeError。其中 18 个包含 SSL/TLS 错误，021 为索引 JSON 解析错误。它们全部属于安装失败，不是模型正常作答后的零分。

补跑清单已固定为 `tua/local/h-setup-repair19.json`，包含原始任务、trial、分类、证据路径以及原始结果 SHA-256。其余 21 个已有评分的任务（5 个满分、16 个零分）不重跑、不改分。

| ID | 任务目录 | 上次异常 |
|---|---|---|
| 012 | 012-hide-na-budget-values | SSL/TLS 下载错误 |
| 014 | 014-pivot-promo-revenue | SSL/TLS 下载错误 |
| 020 | 020-calculate-period-rate | SSL/TLS 下载错误 |
| 021 | 021-fill-ramp-chart | pip 索引 JSON 解析错误 |
| 043 | 043-load-hello-extension | SSL/TLS 下载错误 |
| 047 | 047-set-bing-search | SSL/TLS 下载错误 |
| 076 | 076-make-src-gif-clip | SSL/TLS 下载错误 |
| 077 | 077-corresponding-scholar-url | SSL/TLS 下载错误 |
| 079 | 079-fix-mp3-metadata | SSL/TLS 下载错误 |
| 080 | 080-convert-novel-epub | SSL/TLS 下载错误 |
| 081 | 081-video-frame-slide-bg | SSL/TLS 下载错误 |
| 083 | 083-gemini-responses-docx | SSL/TLS 下载错误 |
| 085 | 085-webext-happy-scaffold | SSL/TLS 下载错误 |
| 097 | 097-slides-to-document | SSL/TLS 下载错误 |
| 102 | 102-daily-email-report | 安装/构建依赖时 SSL/TLS 错误 |
| 106 | 106-create-charles-ssh-user | SSL/TLS 下载错误 |
| 116 | 116-bottom-left-page-numbers | SSL/TLS 下载错误 |
| 117 | 117-comma-text-to-table | SSL/TLS 下载错误 |
| 118 | 118-set-times-new-roman | SSL/TLS 下载错误 |

## 补跑命令

保持 H-qwen 全开配置、OpenRouter Qwen3.7 Flash、原 fork wheel、每题一次；使用修复后的离线依赖安装器。当前 H-qwen YAML 哈希已与原运行 manifest 核对一致。

在已设置 OPENROUTER_API_KEY 的终端执行：

```bash
cd '/Users/xumuqiu/Desktop/Tri1材料/PE6203/6203_GP_2/mini-swe-agent-tua'
caffeinate -i bash run-previous40.sh run \
  --configs H-qwen \
  --only-file tua/local/h-setup-repair19.json \
  --parallel 1 --concurrency 1 --attempts 1 \
  --batch "jobs/h-repair19-$(date +%Y%m%d-%H%M%S)"
```

本轮只创建 19 个 trial，同时最多一个任务容器；可与现有 E/Q 实验并行。不会覆盖上次的 40 题结果。启动器的 manifest 会同时记录原固定 40 题、实际选择的 19 题和选择文件校验值，避免把补跑误称为一轮完整 40 题。

只打印执行计划、不调用模型：

```bash
bash run-previous40.sh plan --configs H-qwen \
  --only-file tua/local/h-setup-repair19.json \
  --parallel 1 --concurrency 1 --attempts 1
```

已经检查该计划包含且仅包含上述 19 个不重复任务；没有因零分挑选任务。计划快照为 `tua/local/h-setup-repair19-plan.txt`。

## 结果解释

可将原 21 个有评分任务与这次对应的 19 个补跑记录组成覆盖 40 题的“安装修复后补全结果”，同时保留并标注原始运行和补跑来源，不应称为同一环境下一次独立完成的 40 题实验。依赖安装方式和传递依赖已锁定，其他评分素材、模型 API 等网络链路仍可能出现问题。

本次准备过程没有启动模型请求。当前助手执行环境中未设置 OPENROUTER_API_KEY，需要在用户已有密钥的终端执行上述命令；不需要复制或公开密钥。
