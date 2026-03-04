from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.contracts import ErrorSchema
from knowledge.providers import HybridKnowledgeProvider, LocalKnowledgeProvider, resolve_knowledge_provider


class _StubProvider:
    def __init__(self, name: str, result=None, raise_error: bool = False) -> None:
        self.name = name
        self._result = result if result is not None else []
        self._raise_error = raise_error

    def retrieve(self, base_dir: Path, error: ErrorSchema):
        del base_dir, error
        if self._raise_error:
            raise RuntimeError("boom")
        return list(self._result)


class KnowledgeProviderTests(unittest.TestCase):
    def test_local_provider_retrieves_hits_from_error_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            knowledge_dir = base_dir / "knowledge"
            knowledge_dir.mkdir(parents=True)
            (knowledge_dir / "error_patterns.yaml").write_text(
                '- id: compile-hint\n  keywords: ["compile"]\n  guidance: "check compile command"\n',
                encoding="utf-8",
            )
            (knowledge_dir / "cangjie_recipes.md").write_text("", encoding="utf-8")
            (knowledge_dir / "project_conventions.md").write_text("", encoding="utf-8")
            error = ErrorSchema(
                category="compile",
                file="src/main.cj",
                line=1,
                message="compile failed",
                context="compile failed with exit code 2",
                fingerprint="fp1",
            )

            provider = LocalKnowledgeProvider()
            hits = provider.retrieve(base_dir, error)

            self.assertTrue(hits)
            self.assertEqual(hits[0].title, "compile-hint")

    def test_resolve_knowledge_provider_supports_all_modes(self) -> None:
        local = resolve_knowledge_provider("local")
        mcp = resolve_knowledge_provider("mcp")
        hybrid = resolve_knowledge_provider("hybrid")
        self.assertEqual(local.mode, "local")
        self.assertEqual(mcp.mode, "mcp")
        self.assertEqual(hybrid.mode, "hybrid")
        self.assertEqual(local.provider.name, "local")
        self.assertEqual(mcp.provider.name, "mcp")
        self.assertEqual(hybrid.provider.name, "hybrid")

    def test_resolve_knowledge_provider_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            resolve_knowledge_provider("unknown")

    def test_hybrid_provider_uses_mcp_hits_when_available(self) -> None:
        hybrid = HybridKnowledgeProvider(
            mcp_provider=_StubProvider("mcp", result=["mcp-hit"]),
            local_provider=_StubProvider("local", result=["local-hit"]),
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="compile failed",
            context="ctx",
            fingerprint="fp-h1",
        )

        hits = hybrid.retrieve(Path("."), error)

        self.assertEqual(hits, ["mcp-hit"])

    def test_hybrid_provider_falls_back_to_local_on_mcp_error(self) -> None:
        hybrid = HybridKnowledgeProvider(
            mcp_provider=_StubProvider("mcp", raise_error=True),
            local_provider=_StubProvider("local", result=["local-hit"]),
        )
        error = ErrorSchema(
            category="compile",
            file="src/main.cj",
            line=1,
            message="compile failed",
            context="ctx",
            fingerprint="fp-h2",
        )

        hits = hybrid.retrieve(Path("."), error)

        self.assertEqual(hits, ["local-hit"])


if __name__ == "__main__":
    unittest.main()
