# -*- coding: utf-8 -*-
"""Cliente JSON-RPC real para servidores MCP via stdio."""
from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import threading
import shutil
from typing import Any


class MCPStdioClient:
    """Executa initialize/tools/list/tools/call com um servidor MCP real."""

    def __init__(self, command: str, args: list[str] | None = None, timeout: float = 20.0,
                 env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self.timeout = timeout
        self.env = env
        self.process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._next_id = 1

    def start(self) -> dict[str, Any]:
        if self.process and self.process.poll() is None:
            return self.initialize()
        try:
            command = self.command
            args = list(self.args)
            if os.name == "nt" and command.lower().endswith(("npx.ps1", "npm.ps1")):
                command = os.environ.get("COMSPEC", "cmd.exe")
                args = ["/d", "/s", "/c", self.command, *args]
            self.process = subprocess.Popen(
                [command, *args], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=self.env,
            )
            return self.initialize()
        except Exception as exc:
            return {"ok": False, "error": f"falha ao iniciar: {exc}"}

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            return {"ok": False, "error": "processo MCP não iniciado"}
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                payload["params"] = params
            try:
                self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.process.stdin.flush()
                responses: queue.Queue[str | None] = queue.Queue()

                def read_line() -> None:
                    try:
                        responses.put(self.process.stdout.readline())
                    except Exception:
                        responses.put(None)

                while True:
                    threading.Thread(target=read_line, daemon=True).start()
                    try:
                        line = responses.get(timeout=self.timeout)
                    except queue.Empty:
                        return {"ok": False, "error": f"timeout de {self.timeout:g}s aguardando {method}"}
                    if not line:
                        return {"ok": False, "error": "servidor MCP encerrou o stdout"}
                    try:
                        response = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if response.get("id") != request_id:
                        continue
                    if "error" in response:
                        return {"ok": False, "error": str(response["error"])}
                    return {"ok": True, "result": response.get("result")}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def initialize(self) -> dict[str, Any]:
        result = self._request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "XAU_AI_PRO", "version": "1.3.2"},
        })
        if not result.get("ok"):
            return result
        self._notify("notifications/initialized")
        tools = self._request("tools/list", {})
        if tools.get("ok"):
            result["tools"] = (tools.get("result") or {}).get("tools", [])
        return result

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if not self.process or not self.process.stdin:
            return
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except Exception:
            pass

    def list_tools(self) -> dict[str, Any]:
        return self._request("tools/list", {})

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


def stdio_from_endpoint(endpoint: str, extra_env: dict[str, str] | None = None) -> MCPStdioClient:
    parts = shlex.split(endpoint, posix=False)
    if not parts:
        raise ValueError("endpoint stdio vazio")
    command = parts[0].strip('"')
    # No Windows, npx/npm são wrappers .cmd e não podem ser encontrados
    # diretamente por CreateProcess sem resolução explícita.
    if os.name == "nt" and command.lower() in {"npx", "npm", "node", "uvx"}:
        resolved = shutil.which(command) or shutil.which(command + ".cmd")
        if not resolved and command.lower() in {"npx", "npm"}:
            resolved = shutil.which(command + ".ps1")
        if resolved:
            command = resolved
    process_env = os.environ.copy()
    process_env.update(extra_env or {})
    return MCPStdioClient(command, [p.strip('"') for p in parts[1:]], env=process_env)
