# Cangjie Build-Repair Kit：项目说明与进展

## 1. 这个项目要解决什么问题

在仓颉项目里，用大模型或 Agent 写代码并不难，真正耗时的是后续的调试与验证。

最常见的重复动作是：执行构建、读报错、改代码、再构建。这个动作本身不复杂，但在不同项目（UI / non-UI）上的命令、目录和约束差异很大，导致流程难复用、结果难审计。再加上直接让 AI 自由调试通常发散、上下文容易丢失，因此考虑把这条链路流程化，做成可复用框架：

`Build -> Diagnose -> Plan -> Patch -> Verify -> Record`

核心边界是：

- 项目差异通过配置处理（命令、工作目录、可修改路径、产物检查）。
- 修复策略与执行器分离（策略只出计划，补丁必须通过 PatchApplier 落地）。
- 每一轮都有结构化产物，便于排查和回归。

---

## 2. 当前进度（代码已实现）

### 2.1 主流程和模块

- 主循环：`driver/loop.py`
- 构建适配：`adapters/cjpm_adapter.py`、`adapters/hvigor_adapter.py`
- 统一验证：`driver/verifier.py`（build/test/artifact）
- 错误解析：`repair/error_parser.py`（含稳定 fingerprint）
- 补丁执行：`repair/patcher.py`（dry-run、失败回滚、路径/行数限制）
- 策略接口：`repair/strategies/base.py`
- 规则策略：`repair/strategies/rule_based.py`
- LLM 协议与 mock：`repair/strategies/llm.py`、`repair/strategies/mock_llm.py`

### 2.2 可审计输出

每次运行会在 `runs/<run_id>/` 下生成：

- `error_iter_<n>.json`
- `patch_plan_iter_<n>.json`
- `iter_<n>.json`
- `verify_iter_<n>.log`
- `patch_iter_<n>.diff`
- `summary.json`
- `report.md`

这里将输出格式固定，把关键结果按固定字段写入 JSON/Markdown，方便后续做检索、对比和回归统计。


### 2.3 当前验证基线

截至当前提交（`d12680d`）：

- 自动化测试：`python3 -m unittest discover -s tests -q`
- 最新结果：`Ran 37 tests ... OK`

当前版本已经可以作为“可运行、可验证、可追踪”的修复框架使用

---

## 3. 后续计划（按当前条件调整）

当前已经有可尝试的 MCP，因此考虑：先 MCP、再真实 LLM、最后多模型。

### 阶段 1：先接入 MCP（3-5 天）

目标：

- 在 `knowledge` 层落地 provider 机制：`local | mcp | hybrid`。
- 当前已有可用 MCP，计划打通错误上下文 -> 知识检索 -> 结构化返回链路。
- 保留 local 回退，避免 MCP 波动影响主流程。

交付标准：

- 同一错误在 local 与 mcp 模式下都能返回可追溯来源（`source` 字段可核对）。
- MCP 不可用时自动回退 local，`run` 不中断。

### 阶段 2：接入真实 LLM（1-2 周）

目标：

- 把 `MockLLMStrategy` 替换为真实模型调用实现。
- 默认读取 MCP/Local 的检索结果，减少无依据修改。
- 约束模型只能输出 `PatchPlan`，不能直接写文件。

交付标准：

- 在至少 1 个 non-UI 样例上，规则策略无法处理时，LLM 策略能给出可执行 patch 计划。
- 审计产物完整落盘（error / patch_plan / diff / summary）。

### 阶段 3：多模型扩展（1 周）

目标：

- 在策略层支持多模型路由（按错误类型或复杂度选择 provider）。
- 保持最小路由规则，不引入复杂编排。

交付标准：

- 至少 2 个模型 provider 可配置切换。
- 同一输入可复现路由决策与结果记录。

---

## 4. 如何在项目上试用（具体步骤）

### 4.1 首次接入新工程

1. 生成配置：

```bash
python3 -m driver.main init --template non_ui --output-dir ./my-configs --project-name myproj --workdir /path/to/project
```

2. 修改配置中的 4 个关键项：`verify_command`、`test_command`、`editable_paths`、`artifact_checks`。

3. 先做可执行性校验：

```bash
python3 -m driver.main validate --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

4. 运行一次闭环：

```bash
python3 -m driver.main run --project-config ./my-configs/project.myproj.toml --policy-config ./my-configs/policy.default.toml
```

5. 检查 `runs/<run_id>/summary.json` 与 `report.md`，确认是成功、失败还是安全停止。

---

## 5. 应用场景

1. 新项目初始化  
   用统一流程替代“每个项目各写一套调试脚本”的方式。

2. 团队回归与持续集成  
   对失败构建产出结构化诊断记录，便于复盘与追踪。

3. LLM 修复系统的执行底座  
   把模型能力限制在“出方案”，把真正改文件与门禁校验收敛到执行层。

---

## 6. 期望效果与评估方式

我并不期望带来“自动化程度最高”的工具，而是希望得到“流程化调试比盲目调试更稳妥高效”的工具。

### 6.1 使用预期

使用者应能感受到三点：

1. 失败可定位：每轮错误、计划、补丁和结果都有记录，不需要反复翻原始日志。  
2. 修改可控：即使接入 LLM，也不会出现任意文件被改动的情况。  
3. 调试可复现：同样输入可以复跑，便于团队协作和回归。

### 6.2 评估指标

1. 成功率：在样本集上 `final_status=success` 的比例。  
2. 平均轮次：成功样本的平均迭代次数。  
3. 平均耗时：从开始到停止的总时长。  
4. 安全事件数：越界修改、绕过 PatchApplier、不可追溯修改次数（目标为 0）。  
5. 可迁移成本：新项目接入时，除配置外是否需要改框架代码（目标接近 0）。

如果连续两周在以上指标上优于“直接自由式 LLM/Agent 调试”，就说明这个工具在工程实践上成立，可以继续推进多模型扩展。
