# Milestone G1-G5 Multi-Model Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成最小多模型路由：支持至少 2 个模型切换、按错误类型/复杂度路由、记录可追踪决策、验证可复现性，并输出周度对比报表。

**Architecture:** 引入 `MultiModelLLMStrategy` 作为策略层路由封装（不污染 loop 核心）；`run_loop` 仅消费策略输出并记录路由决策。周报模块读取 `runs/*` 产物聚合成功率/轮次/耗时/安全事件。

**Tech Stack:** Python dataclass + unittest + 现有 run artifacts。

---

### Task 1: G1/G2 RED - 路由与配置行为测试

**Files:**
- Create: `tests/test_multi_model_routing.py`
- Modify: `tests/test_validate_command.py`

**Steps:**
1. 写测试：`repair_strategy=multi_llm` 下 primary/secondary 可切换
2. 写测试：按错误类型与复杂度选择模型
3. 写测试：非法路由配置在 validate 阶段失败
4. 运行：`python3 -m unittest tests/test_multi_model_routing.py tests/test_validate_command.py -q`（预期 FAIL）

### Task 2: G1/G2/G3 GREEN - 实现多模型路由与决策记录

**Files:**
- Create: `repair/strategies/multi_llm.py`
- Modify: `repair/strategies/__init__.py`
- Modify: `driver/contracts.py`
- Modify: `driver/loop.py`
- Modify: `driver/main.py`
- Modify: `configs/project.nonui.sample.toml`
- Modify: `configs/project.helloworld.toml`
- Modify: `configs/project.nonui.context7.sample.toml`

**Steps:**
1. 实现路由策略（error_type/complexity）
2. 接入 `repair_strategy=multi_llm`
3. 在 iter 记录中写入 `model_route_decision`
4. 运行：`python3 -m unittest tests/test_multi_model_routing.py -q`（预期 PASS）

### Task 3: G4 RED/GREEN - 可复现性回归

**Files:**
- Create: `tests/test_routing_reproducibility.py`

**Steps:**
1. 写测试：相同输入两次路由决策完全一致
2. 运行并修复到 PASS

### Task 4: G5 RED/GREEN - 周度对比报表

**Files:**
- Create: `driver/weekly_report.py`
- Create: `tests/test_weekly_report.py`
- Modify: `driver/main.py`

**Steps:**
1. 写测试：周报输出包含成功率/轮次/耗时/安全事件
2. 实现 `weekly-report` 子命令
3. 运行：`python3 -m unittest tests/test_weekly_report.py -q`

### Task 5: 全量回归与文档

**Files:**
- Modify: `docs/development_assessment_and_followup.md`

**Steps:**
1. 全量：`python3 -m unittest discover -s tests -q`
2. 勾选 G1-G5 并追加 Update
3. 再跑一次全量确认最终状态
