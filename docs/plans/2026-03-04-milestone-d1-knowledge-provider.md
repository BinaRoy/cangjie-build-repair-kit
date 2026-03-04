# Milestone D1 Knowledge Provider Abstraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现知识检索层 `KnowledgeProvider` 抽象与 `local|mcp|hybrid` provider 配置入口，并确保当前 local 行为不回归。

**Architecture:** 在 `knowledge` 层新增 provider 抽象与解析器，`driver/loop.py` 只依赖抽象接口，默认绑定 local provider。`ProjectConfig` 扩展 provider 配置并在初始化时校验合法值，`validate` 命令可提前阻断非法配置。

**Tech Stack:** Python 3.10+ dataclasses, unittest, 现有 driver/repair/knowledge 模块。

---

### Task 1: 通过测试定义 D1 行为边界

**Files:**
- Create: `tests/test_knowledge_provider.py`
- Modify: `tests/test_loop_contracts.py`
- Modify: `tests/test_validate_command.py`

**Step 1: Write the failing test**

```python
# tests/test_knowledge_provider.py
# 1) local provider 可用
# 2) resolve_provider 支持 local/mcp/hybrid
# 3) 非法 provider 抛出 ValueError
```

```python
# tests/test_loop_contracts.py
# strategy context 必须包含 knowledge_provider_mode / knowledge_provider_name
```

```python
# tests/test_validate_command.py
# knowledge_provider 非法值时 validate 返回 1
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_knowledge_provider.py tests/test_loop_contracts.py tests/test_validate_command.py -q`
Expected: FAIL（缺少 provider 抽象与上下文字段/校验）

### Task 2: 最小实现 provider 抽象与配置

**Files:**
- Create: `knowledge/providers.py`
- Modify: `knowledge/retriever.py`
- Modify: `driver/contracts.py`
- Modify: `driver/loop.py`

**Step 1: Write minimal implementation**

```python
# knowledge/providers.py
# - KnowledgeProvider protocol
# - LocalKnowledgeProvider
# - resolve_knowledge_provider(mode)
```

```python
# driver/contracts.py
# - ProjectConfig 增加 knowledge_provider: str = "local"
# - __post_init__ 校验 local|mcp|hybrid
```

```python
# driver/loop.py
# - 使用 provider.retrieve(base_dir, error)
# - strategy_context 新增 provider 字段
```

**Step 2: Run test to verify it passes**

Run: `python3 -m unittest tests/test_knowledge_provider.py tests/test_loop_contracts.py tests/test_validate_command.py -q`
Expected: PASS

### Task 3: 全量回归与文档同步

**Files:**
- Modify: `docs/development_assessment_and_followup.md`

**Step 1: Run full tests**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS

**Step 2: Update development tracking doc**

- 勾选 `D1`
- 追加 `### Update 2026-03-04`（变更、影响模块、验证命令、结果、风险）

**Step 3: Final verification**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS（文档修改不影响代码，确保最终状态一致）
