# Cangjie Build-Repair 工程评估与后续开发跟踪（2026-03-04）

## 0. 文档目的

本文件作为当前仓库的统一开发基线，覆盖：

1. 当前工程扫描结果  
2. 与 `DEVELOPMENT_GUIDE` 的逐项对比  
3. 重构与开发优先级  
4. 可执行、可跟踪的后续迭代清单  
5. 每次开发后的维护更新规范  

---

## 1. 第一步：工程扫描（现状）

### 1.1 当前模块划分

- 入口与编排：`driver/main.py`、`driver/loop.py`
- 配置与数据结构（schema）：`driver/contracts.py`
- 运行记录与报告：`driver/state_store.py`、`driver/reporting.py`
- 构建执行适配层：`adapters/base.py`、`adapters/cjpm_adapter.py`、`adapters/hvigor_adapter.py`
- 错误解析/修复策略/补丁执行/门禁：`repair/error_parser.py`、`repair/planner.py`、`repair/patcher.py`、`repair/validators.py`
- 知识检索：`knowledge/retriever.py`、`knowledge/error_patterns.yaml`
- 测试：`tests/test_validate_command.py`、`tests/test_dual_gate_adapters.py`

### 1.2 已实现功能列表

- 已有完整主循环（构建失败 -> 解析 -> 检索 -> 计划 -> 应用 -> 校验 -> 记录）
- 支持 preflight（Windows 工具链可用性检查）
- 支持 dual-gate（build 成功后执行 test）
- 支持 patch 安全门禁（改单文件数/行数/可编辑路径/脚手架词检测）
- 支持结构化运行产出（`runs/<run_id>/iter_*.json`、`summary.json`、`report.md`）
- 支持模板化配置生成、配置校验、产品打包导出

### 1.3 当前阶段剩余关键能力（下一阶段目标）

- MCP 知识源尚未接入主检索链路（当前以本地检索为主）
- 失败案例归档与复用机制尚未落地（未形成可检索 case memory）
- 真实 LLM provider 尚未接入（当前为 mock 策略）
- 多模型路由策略尚未落地（当前单策略主导）

### 1.4 潜在耦合风险

- `driver/loop.py` 直接依赖 `repair.*` 具体实现，策略替换成本偏高
- `ErrorBlock` 语义偏轻，导致后续策略/统计只能基于字符串猜测
- 验证成功标准分散在 adapter 内（特别是产物检查），不利于统一扩展

---

## 2. 第二步：与 Development Guide 对比

### 2.1 合格项（已满足或基本满足）

- 存在 LoopController 职责主体：`driver/loop.py`
- 模块分层基本清晰（driver/adapters/repair/knowledge）
- 存在结构化 schema：`driver/contracts.py`
- 存在运行记录机制：`StateStore` + `reporting`
- Patch 有安全约束（文件范围、行数限制、scaffold 检测）

### 2.2 历史不符合项（已关闭）

- `fingerprint` 缺失 -> 已实现稳定指纹
- `LogParser` 字段不完整 -> 已升级为结构化 ErrorSchema
- patch 无回滚与 diff -> 已支持 dry-run/rollback/diff
- 策略不可插拔 -> 已完成 RepairStrategy 抽象与 mock LLM 协议
- loop 与模块耦合高 -> 已支持依赖注入与契约测试

### 2.3 当前新增关注项（下一阶段）

- 知识层 provider 扩展（local/mcp/hybrid）
- 经验复用（failure case 归档与检索）
- 真实 LLM 集成下的安全与可解释性
- 多模型路由下的可复现性
### 2.4 下一阶段优先级排序

- P0（立刻）：MCP 接入与回退机制（不中断 run）
- P1（短期）：failure case 归档与检索复用
- P2（中期）：真实 LLM 接入与多模型路由

---

## 3. 第三步：改进建议（当前阶段定位）

当前仓库已完成基础可控闭环（A/B/C），并具备“规则 + mock LLM + 安全门禁 + 可审计产物”的初步模型。下一阶段重点从“能跑”转为“能持续学会修”。

下一阶段最小目标：

1. 知识输入升级：接入 MCP，但保持 local 回退  
2. 经验可复用：落地 failure case 归档与检索  
3. 模型可控升级：接入真实 LLM，仍只允许输出 PatchPlan  
4. 策略可扩展：支持最小多模型路由并可复现

---

## 4. 后续开发执行清单（可 follow）

### Milestone A（P0）审计与可回滚闭环

- [x] A1. 定义 `ErrorSchema`：`category/file/line/message/context/fingerprint`
- [x] A2. 升级 `error_parser` 输出并保证 fingerprint 稳定
- [x] A3. `StateStore` 增加 `write_error`/`write_patch_plan`/`write_patch_diff`
- [x] A4. `PatchApplier` 增加 dry-run 与最小 rollback（失败后自动恢复原文）
- [x] A5. `run_loop` 按迭代输出 `error.json` 与 `patch_plan.json`
- [x] A6. 增加回归测试：fingerprint 稳定性、rollback 生效、产物文件存在

### Milestone B（P1）模块边界重构

- [x] B1. 新增 `repair/strategies/base.py`（`propose(error, context)->PatchPlan`）
- [x] B2. 将当前规则策略迁移到 `repair/strategies/rule_based.py`
- [x] B3. 新增 `driver/verifier.py`，统一 build/test/artifact 判定
- [x] B4. `loop` 改为依赖注入：parser/strategy/applier/verifier
- [x] B5. 增加接口契约测试，防止模块直接耦合回退

### Milestone C（P2）LLM 接入前置设计（不接入真实 LLM）

- [x] C1. 定义 `LLMStrategy` 输入/输出 schema（仅协议）
- [x] C2. 增加 mock strategy 适配层，验证不绕过 PatchApplier
- [x] C3. 明确安全红线测试：不得直接写文件/不得控制 loop

### Milestone D（P0）MCP 知识接入（3-5 天）

- [ ] D1. 定义 `KnowledgeProvider` 抽象与 provider 配置项（`local|mcp|hybrid`）
- [ ] D2. 实现 MCP provider 适配层（输入错误上下文，输出结构化 KnowledgeItem）
- [ ] D3. 实现 hybrid 回退策略（MCP 失败自动回落 local）
- [ ] D4. 在 `iter_<n>.json` 中补充 `knowledge_sources` 与 provider 决策记录
- [ ] D5. 增加回归测试：MCP 正常、MCP 失败回退、source 可追溯

### Milestone E（P1）失败案例归档与复用（1 周）

- [ ] E1. 设计 `failure_cases/` 数据结构（fingerprint、上下文、plan、result、case_id）
- [ ] E2. 每轮失败自动写入 case 归档（去重策略按 fingerprint）
- [ ] E3. 方案生成前接入相似 case 检索（Top-K）
- [ ] E4. 在 patch 计划中记录引用 case_id 与命中理由
- [ ] E5. 增加回归测试：同类错误二次出现时命中历史 case

### Milestone F（P2）真实 LLM 接入（1-2 周）

- [ ] F1. 用真实 provider 替换 `MockLLMStrategy`（保留接口不变）
- [ ] F2. 强制 LLM 输入包含：错误结构化对象 + 知识来源 + 历史 case
- [ ] F3. 强制 LLM 输出校验：仅允许结构化 PatchPlan
- [ ] F4. 增加安全回归：禁止直写、越界修改、无证据 patch
- [ ] F5. 在 1 个 non-UI 样例验证“规则失败但 LLM 可修复”

### Milestone G（P2）多模型最小路由（1 周）

- [ ] G1. 增加模型 provider 配置（至少 2 个可切换）
- [ ] G2. 增加路由规则（按错误类型/复杂度）
- [ ] G3. 路由决策写入迭代记录（可追踪）
- [ ] G4. 增加可复现性回归：同输入同路由结果
- [ ] G5. 输出周度对比报表（成功率/轮次/耗时/安全事件）

---

## 5. 验证基线（每次迭代都要跑）

当前环境实际检查（2026-03-04）：

- `python3 -m unittest discover -s tests -q` 可执行且通过（37 tests）

后续统一验证命令建议：

1. `python3 -m unittest discover -s tests -q`
2. `python3 -m driver.main validate --project-config <...> --policy-config <...>`
3. 至少 1 组 `cangjie-repair run` 冒烟（UI 或 non-UI）

---

## 6. 维护规则（必须遵守）

每次开发完成后，必须同步更新本文件以下区域：

- “第 4 节执行清单”的勾选状态
- 新增/变更模块的路径与职责
- 新增 schema 字段与样例
- 验证结果（通过/失败、失败原因）

推荐更新模板：

```md
### Update YYYY-MM-DD
- 变更: ...
- 影响模块: ...
- 验证命令: ...
- 结果: ...
- 风险/待办: ...
```

---

## 7. 会话续接脚本（新 session 快速跟进）

### 7.1 生成项目快照（推荐每次改动后执行）

- CLI:
  `python3 -m driver.main snapshot --output docs/session_snapshot.md --source-doc docs/development_assessment_and_followup.md`
- Bash:
  `scripts/session_snapshot.sh`
- PowerShell:
  `scripts/session_snapshot.ps1`

作用：

- 记录当前分支、最新提交、工作区变更
- 自动提取本文件中的里程碑 checkbox，形成“下一会话待办”
- 让新 session 在 1 个文件中快速恢复上下文

### 7.2 追加开发更新记录（每次功能改动后执行）

- CLI:
  `python3 -m driver.main doc-update --date <YYYY-MM-DD> --change "<变更>" --modules "<a.py,b.py>" --verify-command "<cmd>" --result "<PASS|FAIL>" --risk "<风险>"`
- Bash:
  `scripts/doc_update.sh <date> <change> <modules_csv> <verify_cmd> [result] [risk]`
- PowerShell:
  `scripts/doc_update.ps1 -DateText <date> -ChangeText <change> -ModulesCsv <csv> -VerifyCommand <cmd> [-ResultText PASS] [-RiskText "..."]`

---

## 8. 当前结论（一句话）

工程基础闭环（A/B/C）已完成，下一阶段进入“Agent 协同可控修复”建设：优先落地 MCP 知识接入与 failure case 复用，再接真实 LLM 与多模型路由。

### Update 2026-03-04
- 变更: 将后续执行清单从 A/B/C 完结阶段切换为 D/E/F/G（MCP -> case memory -> real LLM -> multi-model）
- 影响模块: docs/development_assessment_and_followup.md
- 验证命令: 文档更新（无代码变更）
- 结果: PASS
- 风险/待办: D1-D5 尚未开始，需要先确定 MCP provider 接口与配置字段

### Update 2026-03-03
- 变更: 新增会话快照与文档维护脚本，并接入 CLI 子命令
- 影响模块: driver/session_snapshot.py, driver/doc_maintenance.py, driver/main.py, scripts/session_snapshot.sh, scripts/session_snapshot.ps1, scripts/doc_update.sh, scripts/doc_update.ps1, tests/test_session_snapshot.py, tests/test_doc_maintenance.py, tests/test_validate_command.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS（11 tests）
- 风险/待办: 仍需按 Milestone A 推进 error schema/fingerprint/rollback

### Update 2026-03-03
- 变更: 新增 ErrorSchema 数据结构并补充字段完整性测试
- 影响模块: driver/contracts.py, tests/test_error_schema.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: A2 尚未开始：error_parser 尚未输出 file/line/fingerprint

### Update 2026-03-03
- 变更: 升级 error_parser 输出为 ErrorSchema，并实现稳定 fingerprint 归一化
- 影响模块: repair/error_parser.py, driver/contracts.py, tests/test_error_parser.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: A3/A5 未完成：error.json 与 patch_plan.json 尚未落盘

### Update 2026-03-03
- 变更: StateStore 新增 error/patch_plan/patch_diff 持久化接口并补充回归测试
- 影响模块: driver/state_store.py, tests/test_state_store.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: A5 未完成：loop 尚未调用新接口产出 error.json/patch_plan.json

### Update 2026-03-03
- 变更: PatchApplier 新增 dry-run 与失败自动回滚，并补充回归测试
- 影响模块: repair/patcher.py, tests/test_patcher.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: A5 未完成：loop 尚未落盘 error.json/patch_plan.json

### Update 2026-03-03
- 变更: run_loop 按失败迭代落盘 error 与 patch_plan 产物，并补充回归测试
- 影响模块: driver/loop.py, tests/test_loop_artifacts.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: A6 未完成：尚缺 rollback 生效与产物存在的更完整回归集合

### Update 2026-03-03
- 变更: 新增 A6 回归测试集（fingerprint/rollback/artifacts），并修复 loop 早停分支 patch_plan 结构化落盘
- 影响模块: tests/test_regression_a6.py, driver/loop.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: Milestone A 已完成，下一阶段进入 B1 接口抽象

### Update 2026-03-03
- 变更: 新增策略抽象接口 RepairStrategy 与契约测试（B1）
- 影响模块: repair/strategies/base.py, repair/strategies/__init__.py, tests/test_strategy_base.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: B2 未完成：规则策略尚未迁移到 repair/strategies/rule_based.py

### Update 2026-03-03
- 变更: 将规则策略迁移至 repair/strategies/rule_based.py，planner 改为委托策略实现
- 影响模块: repair/strategies/rule_based.py, repair/strategies/__init__.py, repair/planner.py, tests/test_rule_based_strategy.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: B3/B4 未完成：verifier 抽象与 loop 依赖注入仍待推进

### Update 2026-03-03
- 变更: 新增 driver/verifier.py 统一 build/test/artifact 判定，并让 cjpm/hvigor adapter 复用
- 影响模块: driver/verifier.py, adapters/cjpm_adapter.py, adapters/hvigor_adapter.py, tests/test_verifier.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: B4 未完成：loop 仍直接依赖 repair.*，尚未完成依赖注入

### Update 2026-03-03
- 变更: run_loop 支持 parser/strategy/applier/verifier 依赖注入，并新增注入回归测试
- 影响模块: driver/loop.py, tests/test_loop_injection.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: B5 未完成：接口契约测试仍需系统化覆盖

### Update 2026-03-03
- 变更: 新增 loop 接口契约测试并固定 strategy context 字段，防止依赖注入回退
- 影响模块: tests/test_loop_contracts.py, driver/loop.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: Milestone B 已完成，下一阶段进入 C1 协议定义

### Update 2026-03-03
- 变更: 新增 LLMStrategy 输入/输出 schema 协议与适配基类，不接真实 LLM（C1）
- 影响模块: repair/strategies/llm.py, repair/strategies/__init__.py, tests/test_llm_strategy_schema.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: C2 未完成：尚缺 mock strategy 适配层与 PatchApplier 链路验证

### Update 2026-03-03
- 变更: 新增 MockLLMStrategy 适配层，并通过 loop 集成测试验证不绕过 PatchApplier
- 影响模块: repair/strategies/mock_llm.py, repair/strategies/__init__.py, tests/test_mock_llm_strategy.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: C3 未完成：安全红线测试仍待补齐

### Update 2026-03-03
- 变更: 新增 C3 安全红线测试并在 loop 增加策略直写文件检测与自动恢复
- 影响模块: tests/test_safety_redlines.py, driver/loop.py
- 验证命令: python3 -m unittest discover -s tests -q
- 结果: PASS
- 风险/待办: Milestone C 已完成；后续可进入分支收尾与整体验收
