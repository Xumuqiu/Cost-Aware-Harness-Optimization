> Historical project note. For portable commands, the published task list, baseline identities and current evidence packaging, use [reproduction/README.md](reproduction/README.md).

# 两组组合实验：执行效率与交付质量

沿用 README 的组件实现，减少为两组有方向区分的组合。使用此前固定的 40 题、同一个 fork wheel、OpenRouter Qwen3.7 Flash，每题运行一次。两组共 80 个 trial，不要求额外运行单组件消融。

## 配置与比较逻辑

| 配置 | C1 预算 | C2 恢复 | C3 自检 | C4 压缩 | C5 任务提示词 | 方向 |
|---|---|---|---|---|---|---|
| E-qwen | 开 | 开 | 关 | 开 | 关 | 执行效率：减少循环、观测噪声和上下文开销 |
| Q-qwen | 开 | 开 | 开 | 关 | 开 | 交付质量：保留完整历史观测，依靠任务提示词和提交自检提高产物合规性 |
| H-qwen（已有运行） | 开 | 开 | 开 | 开 | 开 | 全开参考，不要求这次重跑 |

共享 C1、C2，使两组都使用 150 步、2200 秒、命令超时 120 秒、连续格式错误容忍 10 次。模型路由、供应商约束、reasoning、评分器和题单相同。E 使用原版任务模板，Q 使用 C5 模板。

预先设定的假设：E 可能减少输入 token 和耗时，但压缩可能丢失重要信息；Q 可能改善文件结构和提交质量，但自检与更长上下文可能增加开销。**这只是待检验假设，不能保证两组出现分数差异，也不预设哪组更好。**

这属于两条组合策略的探索性比较，不能将观察到的差异单独归因于 C3、C4 或 C5。单次重复也不足以作显著性或稳定性结论。

## 并行运行

当前终端需已设置 OPENROUTER_API_KEY。两组并行且每组并发一题，同时最多两个任务容器。单任务配置最高 4 GiB，建议 Docker Desktop 至少分配 12 GiB 内存，并留意其他容器占用。

```bash
cd '/Users/xumuqiu/Desktop/Tri1材料/PE6203/6203_GP_2/mini-swe-agent-tua'
caffeinate -i bash run-previous40.sh run \
  --configs E-qwen Q-qwen \
  --parallel 2 --concurrency 1 --attempts 1
```

自动创建 jobs/previous40-时间戳，分别保存 E-qwen 和 Q-qwen 的日志与结果。启动器会记录题单、配置和 wheel 哈希，不修改旧 H-qwen 结果。不需要重建 wheel：新增的是实验 YAML，agent 代码未改变。

只打印命令（不调用模型）：

```bash
bash run-previous40.sh plan --configs E-qwen Q-qwen --parallel 2 --concurrency 1 --attempts 1
```

使用新输出目录进行续跑和汇总，将下面的“时间戳”替换为实际目录名。续跑时必须指定这两组，因为原默认配置列表不包含新实验。

```bash
caffeinate -i bash run-previous40.sh resume \
  --configs E-qwen Q-qwen --parallel 2 --batch jobs/previous40-时间戳
bash run-previous40.sh summary --batch jobs/previous40-时间戳
```

## 报告至少比较什么

全 40 题平均 reward、完整通过率、安装/执行异常数、输入和输出 token、模型调用数、agent 执行时间及总时间。对同一道题记录 E/Q 的结果，列出仅 E 通过、仅 Q 通过和共同通过的任务。费用使用相同固定价表估算；Harbor cost=0 不表示免费。

已有 H-qwen 的 40 题结果中，19 题在安装阶段失败。**2026-10-31 已将本机入口改为带版本锁和 SHA-256 校验的离线安装，并在 Python 3.11/3.12 禁网任务容器中验证通过。** 现有两组命令自动使用修复后的安装器，不需要重建 wheel。详见 INSTALLATION_REPAIR.md。该修复不保证作答或评分过程中的联网操作一定成功。

不能把两组安装成功率不同直接解释成开关收益。保留全部 40 题主口径，并把“两组都正常评分”的共同子集对比作为辅助；该辅助口径有选择偏差。

旧 H-qwen 可作带异常标注的背景参考，不能与新两组简单排序后宣称因果效果。若重新修复环境，旧 H-qwen 与新配置的可比性需重新评估。
