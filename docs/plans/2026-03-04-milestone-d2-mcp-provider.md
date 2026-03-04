# Milestone D2 MCP Provider Adapter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在知识检索层实现可调用 MCP 的 provider 适配层，输入错误上下文并输出结构化 `KnowledgeItem`。

**Architecture:** 新增 `knowledge/mcp_provider.py` 封装 stdio MCP 客户端与结果映射；`knowledge/providers.py` 在 `mcp` 模式下返回 MCP provider。`driver/loop.py` 继续通过 provider 抽象调用，不改主循环控制流。

**Tech Stack:** Python 3.10+, subprocess stdio, JSON-RPC over MCP framing, unittest.

---

### Task 1: 先定义 D2 行为测试（RED）

**Files:**
- Create: `tests/test_mcp_provider.py`
- Modify: `tests/test_knowledge_provider.py`

**Step 1: Write failing tests**
- MCP provider 可将 MCP 返回的结构化条目映射为 `KnowledgeItem`
- MCP provider 在文本返回场景可降级生成 `KnowledgeItem`
- `resolve_knowledge_provider("mcp")` 返回 MCP provider（非 local 占位）

**Step 2: Run to confirm FAIL**
Run: `python3 -m unittest tests/test_mcp_provider.py tests/test_knowledge_provider.py -q`
Expected: FAIL（模块/类不存在或行为不匹配）

### Task 2: 最小实现 MCP provider（GREEN）

**Files:**
- Create: `knowledge/mcp_provider.py`
- Modify: `knowledge/providers.py`
- Modify: `driver/contracts.py`
- Modify: `driver/loop.py`
- Modify: `driver/main.py`
- Modify: `configs/project.nonui.sample.toml`
- Modify: `configs/project.helloworld.toml`

**Step 1: Implement minimal MCP adapter**
- `MCPSettings` 配置（command/args/tool_name/timeout/max_items）
- `StdioMCPClient`：initialize + tools/call
- `MCPKnowledgeProvider.retrieve()`：错误上下文 -> MCP 参数 -> `KnowledgeItem` 列表

**Step 2: Wire provider resolution**
- `mcp` 模式解析到 `MCPKnowledgeProvider`
- 配置 schema 增加 MCP 相关字段（默认值）

**Step 3: Run tests to confirm PASS**
Run: `python3 -m unittest tests/test_mcp_provider.py tests/test_knowledge_provider.py -q`
Expected: PASS

### Task 3: 回归与文档同步

**Files:**
- Modify: `docs/development_assessment_and_followup.md`

**Step 1: Run full test suite**
Run: `python3 -m unittest discover -s tests -q`
Expected: PASS

**Step 2: Update tracking doc**
- 勾选 D2
- 追加 Update 记录（变更/模块/验证/结果/风险）

**Step 3: Final verify**
Run: `python3 -m unittest discover -s tests -q`
Expected: PASS
