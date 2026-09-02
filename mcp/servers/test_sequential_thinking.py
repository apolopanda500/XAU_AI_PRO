# -*- coding: utf-8 -*-
"""Teste MCP - Sequential Thinking (JSON-RPC via stdio)."""
import json
import subprocess
import sys
import time

SERVER = "npx -y @modelcontextprotocol/server-sequential-thinking"

proc = subprocess.Popen(
    SERVER,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    shell=True,
)


def send(obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


def read_msg(timeout=20):
    import queue
    import threading

    q: "queue.Queue[str | None]" = queue.Queue()

    def _reader():
        try:
            line = proc.stdout.readline()
            q.put(line if line else None)
        except Exception:
            q.put(None)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    try:
        line = q.get(timeout=timeout)
    except queue.Empty:
        return None
    if line is None:
        return None
    try:
        return json.loads(line)
    except Exception as exc:
        print("PARSE ERR:", line[:200], exc)
        return None


send({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "xau-test", "version": "1.0"},
    },
})
init = read_msg()
if init is None:
    err = proc.stderr.read() or "(sem stderr)"
    print("TIMEOUT initialize ->", str(err)[:300])
    proc.kill()
    sys.exit(1)
print("INITIALIZE ->", init.get("result", {}).get("serverInfo"))

send({"jsonrpc": "2.0", "method": "notifications/initialized"})
time.sleep(0.5)

send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = read_msg()
if tools is None:
    print("TIMEOUT tools/list")
    proc.kill()
    sys.exit(1)
names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
print("TOOLS ->", names)

# Testa invocacao real da ferramenta sequential_thinking
send({
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {
        "name": "sequentialthinking",
        "arguments": {"thought": "Analise XAUUSD: tendencia de alta no H1.", "thoughtNumber": 1, "totalThoughts": 1, "nextThoughtNeeded": True},
    },
})
call = read_msg()
if call is None:
    print("TIMEOUT tools/call")
    proc.kill()
    sys.exit(1)
content = call.get("result", {}).get("content", [])
print("TOOLS/CALL ->", json.dumps(content, ensure_ascii=False)[:400])

proc.kill()
print("TESTE_CONCLUIDO")