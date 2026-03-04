from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib import request

from driver.contracts import ErrorSchema, KnowledgeItem


@dataclass
class MCPSettings:
    command: str = ""
    args: list[str] = field(default_factory=list)
    server_url: str = ""
    headers: list[str] = field(default_factory=list)
    tool_name: str = "query-docs"
    timeout_sec: int = 15
    max_items: int = 5


class MCPClientProtocol(Protocol):
    def __enter__(self) -> "MCPClientProtocol":
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb) -> bool:
        raise NotImplementedError

    def initialize(self) -> None:
        raise NotImplementedError

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class StdioMCPClient:
    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings
        self._next_id = 1
        self._proc: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "StdioMCPClient":
        cmd = [self._settings.command, *self._settings.args]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1)
            except Exception:
                self._proc.kill()
        return False

    def initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "cangjie-repair-template", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        self._notify("notifications/initialized", {})

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": tool_name, "arguments": arguments})
        return result if isinstance(result, dict) else {}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        rid = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            message = self._read()
            if message.get("id") != rid:
                continue
            if "error" in message:
                raise RuntimeError(f"mcp_error:{message['error']}")
            return message.get("result")

    def _send(self, payload: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("mcp client is not started")
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self._proc.stdin.write(header + body)
        self._proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError("mcp client is not started")
        stdout = self._proc.stdout
        headers: dict[str, str] = {}
        while True:
            line = stdout.readline()
            if not line:
                raise RuntimeError("mcp_eof")
            if line in (b"\r\n", b"\n"):
                break
            text = line.decode("utf-8", errors="replace").strip()
            if ":" in text:
                k, v = text.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            raise RuntimeError("mcp_invalid_content_length")
        body = stdout.read(length)
        if not body:
            raise RuntimeError("mcp_empty_body")
        obj = json.loads(body.decode("utf-8", errors="replace"))
        return obj if isinstance(obj, dict) else {}


class HTTPMCPClient:
    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings
        self._next_id = 1
        self._headers = _parse_header_list(settings.headers)

    def __enter__(self) -> "HTTPMCPClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "cangjie-repair-template", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        self._notify("notifications/initialized", {})

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": tool_name, "arguments": arguments})
        return result if isinstance(result, dict) else {}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._post({"jsonrpc": "2.0", "method": method, "params": params}, expect_response=False)

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        rid = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        response = self._post(payload, expect_response=True)
        if "error" in response:
            raise RuntimeError(f"mcp_error:{response['error']}")
        return response.get("result")

    def _post(self, payload: dict[str, Any], expect_response: bool) -> dict[str, Any]:
        if not self._settings.server_url.strip():
            raise RuntimeError("mcp_server_url_missing")
        body = json.dumps(payload).encode("utf-8")
        req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req_headers.update(self._headers)
        req = request.Request(self._settings.server_url, data=body, headers=req_headers, method="POST")
        with request.urlopen(req, timeout=self._settings.timeout_sec) as resp:
            raw = resp.read()
        if not raw:
            return {} if not expect_response else {"result": {}}
        parsed = json.loads(raw.decode("utf-8", errors="replace"))
        return parsed if isinstance(parsed, dict) else {}


class MCPKnowledgeProvider:
    name = "mcp"

    def __init__(
        self,
        settings: MCPSettings,
        client_factory: Callable[[MCPSettings], MCPClientProtocol] | None = None,
        stdio_client_factory: Callable[[MCPSettings], MCPClientProtocol] | None = None,
        http_client_factory: Callable[[MCPSettings], MCPClientProtocol] | None = None,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory
        self._stdio_client_factory = stdio_client_factory or (lambda s: StdioMCPClient(s))
        self._http_client_factory = http_client_factory or (lambda s: HTTPMCPClient(s))
        self._last_decision: dict[str, object] = {}

    def retrieve(self, base_dir: Path, error: ErrorSchema) -> list[KnowledgeItem]:
        del base_dir  # unused by MCP provider
        if not self._settings.server_url.strip() and not self._settings.command.strip():
            self._last_decision = {
                "selected_provider": "mcp",
                "fallback_used": False,
                "reason": "missing_mcp_endpoint",
                "hit_count": 0,
            }
            return []
        arguments = {"query": self._build_query(error)}
        try:
            with self._select_client_factory()(self._settings) as client:
                client.initialize()
                result = client.call_tool(self._settings.tool_name, arguments)
        except Exception as exc:
            self._last_decision = {
                "selected_provider": "mcp",
                "fallback_used": False,
                "reason": "mcp_exception",
                "error": str(exc),
                "hit_count": 0,
            }
            return []
        hits = _result_to_items(result, self._settings.tool_name, self._settings.max_items)
        self._last_decision = {
            "selected_provider": "mcp",
            "fallback_used": False,
            "reason": "mcp_result",
            "hit_count": len(hits),
        }
        return hits

    def _build_query(self, error: ErrorSchema) -> str:
        parts = [error.category, error.message, error.context]
        return " | ".join(x.strip() for x in parts if x and x.strip())

    def _select_client_factory(self) -> Callable[[MCPSettings], MCPClientProtocol]:
        if self._client_factory is not None:
            return self._client_factory
        if self._settings.server_url.strip():
            return self._http_client_factory
        return self._stdio_client_factory

    def get_last_decision(self) -> dict[str, object]:
        return dict(self._last_decision)


def _parse_header_list(entries: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for entry in entries:
        text = str(entry).strip()
        if not text or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            headers[key] = value
    return headers


def _result_to_items(result: dict[str, Any], tool_name: str, max_items: int) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        raw_items = structured.get("items")
        if isinstance(raw_items, list):
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                content = str(it.get("content", "")).strip()
                if not content:
                    continue
                source = str(it.get("source", f"mcp:{tool_name}"))
                title = str(it.get("title", source))
                items.append(KnowledgeItem(source=source, title=title, content=content))
                if len(items) >= max_items:
                    return items

    content = result.get("content")
    if isinstance(content, list):
        idx = 1
        for block in content:
            if not isinstance(block, dict):
                continue
            if str(block.get("type", "")).lower() != "text":
                continue
            text = str(block.get("text", "")).strip()
            if not text:
                continue
            items.append(
                KnowledgeItem(
                    source=f"mcp:{tool_name}",
                    title=f"{tool_name}#{idx}",
                    content=text,
                )
            )
            idx += 1
            if len(items) >= max_items:
                break
    return items
