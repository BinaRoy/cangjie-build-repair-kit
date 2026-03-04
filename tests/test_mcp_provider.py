from __future__ import annotations

import unittest
from typing import Any

from driver.contracts import ErrorSchema
from knowledge.mcp_provider import MCPKnowledgeProvider, MCPSettings


class _FakeClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.last_tool_name = ""
        self.last_arguments: dict[str, Any] | None = None

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def initialize(self) -> None:
        return None

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.last_tool_name = tool_name
        self.last_arguments = dict(arguments)
        return self._response


class _TrackingFactory:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls = 0

    def __call__(self, _settings: MCPSettings) -> _FakeClient:
        self.calls += 1
        return _FakeClient(self.response)


class MCPProviderTests(unittest.TestCase):
    def test_maps_structured_content_items_to_knowledge_items(self) -> None:
        response = {
            "structuredContent": {
                "items": [
                    {"source": "mcp://cangjie/doc1", "title": "doc1", "content": "hint1"},
                    {"source": "mcp://cangjie/doc2", "title": "doc2", "content": "hint2"},
                ]
            }
        }
        provider = MCPKnowledgeProvider(
            settings=MCPSettings(command="fake-mcp"),
            client_factory=lambda _settings: _FakeClient(response),
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=3,
            message="compile failed",
            context="undefined symbol",
            fingerprint="fp",
        )

        hits = provider.retrieve(base_dir=None, error=error)  # type: ignore[arg-type]

        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0].source, "mcp://cangjie/doc1")
        self.assertEqual(hits[1].title, "doc2")

    def test_fallbacks_to_text_content_when_structured_content_missing(self) -> None:
        response = {
            "content": [
                {"type": "text", "text": "first tip"},
                {"type": "text", "text": "second tip"},
            ]
        }
        provider = MCPKnowledgeProvider(
            settings=MCPSettings(command="fake-mcp", tool_name="search_docs"),
            client_factory=lambda _settings: _FakeClient(response),
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="m",
            context="c",
            fingerprint="f",
        )

        hits = provider.retrieve(base_dir=None, error=error)  # type: ignore[arg-type]

        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0].source, "mcp:search_docs")
        self.assertIn("first tip", hits[0].content)

    def test_passes_only_query_argument_for_context7_compatibility(self) -> None:
        response = {"content": [{"type": "text", "text": "tip"}]}
        fake_client = _FakeClient(response)
        provider = MCPKnowledgeProvider(
            settings=MCPSettings(command="fake-mcp", tool_name="query-docs"),
            client_factory=lambda _settings: fake_client,
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=7,
            message="link error",
            context="undefined symbol MainAbility",
            fingerprint="fp-q",
        )

        provider.retrieve(base_dir=None, error=error)  # type: ignore[arg-type]

        self.assertEqual(fake_client.last_tool_name, "query-docs")
        self.assertEqual(list((fake_client.last_arguments or {}).keys()), ["query"])
        self.assertIn("undefined symbol MainAbility", (fake_client.last_arguments or {}).get("query", ""))

    def test_uses_http_client_when_server_url_is_configured(self) -> None:
        stdio_factory = _TrackingFactory({"content": [{"type": "text", "text": "stdio"}]})
        http_factory = _TrackingFactory({"content": [{"type": "text", "text": "http"}]})
        provider = MCPKnowledgeProvider(
            settings=MCPSettings(
                command="unused-stdio",
                server_url="https://mcp.context7.com/mcp",
                headers=["CONTEXT7_API_KEY=test-key"],
                tool_name="query-docs",
            ),
            stdio_client_factory=stdio_factory,
            http_client_factory=http_factory,
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=2,
            message="m",
            context="c",
            fingerprint="f",
        )

        hits = provider.retrieve(base_dir=None, error=error)  # type: ignore[arg-type]

        self.assertEqual(len(hits), 1)
        self.assertIn("http", hits[0].content)
        self.assertEqual(http_factory.calls, 1)
        self.assertEqual(stdio_factory.calls, 0)


if __name__ == "__main__":
    unittest.main()
