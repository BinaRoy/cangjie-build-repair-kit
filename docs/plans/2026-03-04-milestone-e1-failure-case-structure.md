# Milestone E1 Failure Case Structure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 设计并落地 `failure_cases/` 的数据结构（含 case_id、fingerprint、context、plan、result），为 E2 自动归档提供稳定接口。

**Architecture:** 新增 `driver/failure_cases.py`，定义 `FailureCaseRecord` schema 与 `FailureCaseStore` 落盘接口；路径按 fingerprint 分桶，避免文件名非法字符与目录污染。

**Tech Stack:** Python dataclass + json + unittest。

---

### Task 1: RED - 数据结构与落盘契约测试

**Files:**
- Create: `tests/test_failure_cases.py`

**Steps:**
1. 写测试：记录必须包含 `case_id/fingerprint/context/plan/result`
2. 写测试：`FailureCaseStore` 将记录写入 `failure_cases/<fingerprint_bucket>/<case_id>.json`
3. 运行：`python3 -m unittest tests/test_failure_cases.py -q`，预期 FAIL

### Task 2: GREEN - 最小实现

**Files:**
- Create: `driver/failure_cases.py`

**Steps:**
1. 定义 `FailureCaseRecord`
2. 定义 `create_failure_case_record(...)`
3. 定义 `FailureCaseStore.write_case(...)`
4. 运行：`python3 -m unittest tests/test_failure_cases.py -q`，预期 PASS

### Task 3: 回归与文档

**Files:**
- Modify: `docs/development_assessment_and_followup.md`

**Steps:**
1. 全量测试：`python3 -m unittest discover -s tests -q`
2. 勾选 E1 并追加 Update
3. 再跑一次全量测试确认最终状态
