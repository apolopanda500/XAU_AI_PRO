"""Gateway remoto seguro - camada HTTP sem execução habilitada.

Executa somente health, sessão e contratos. O serviço remoto não deve receber
chaves no frontend e rejeita negociação até adaptadores aprovados existirem.
"""
from __future__ import annotations

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from backend.remote_auth import authenticate, login, logout, register

HOST = os.getenv("XAU_REMOTE_HOST", "127.0.0.1")
PORT = int(os.getenv("XAU_REMOTE_PORT", "9443"))
SESSION_TTL = int(os.getenv("XAU_SESSION_TTL", "3600"))
SESSIONS: dict[str, float] = {}


def reply(ok: bool, **data: object) -> bytes:
    return json.dumps({"ok": ok, **data}, ensure_ascii=False).encode("utf-8")


class RemoteHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        return

    def send_json(self, code: int, payload: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_json(200, reply(True, service="remote-gateway", execution_enabled=False, withdrawals_enabled=False))
            return
        self.send_json(404, reply(False, error="not_found"))

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json(400, reply(False, error="invalid_json")); return
        if self.path == "/register":
            try: self.send_json(201, reply(True, user_id=register(str(payload.get("email", "")), str(payload.get("password", "")))))
            except ValueError as exc: self.send_json(422, reply(False, error=str(exc)))
            return
        if self.path == "/login":
            try:
                token, user_id = login(str(payload.get("email", "")), str(payload.get("password", "")))
                self.send_json(200, reply(True, token=token, user_id=user_id, expires_in=SESSION_TTL, execution_enabled=False, withdrawals_enabled=False))
            except PermissionError as exc: self.send_json(401, reply(False, error=str(exc)))
            return
        if self.path == "/logout":
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not token: self.send_json(401, reply(False, error="token_required")); return
            logout(token); self.send_json(200, reply(True, logged_out=True)); return
        if self.path.startswith("/api/universal/"):
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            try: user_id = authenticate(token)
            except PermissionError as exc: self.send_json(401, reply(False, error=str(exc))); return
            self.send_json(501, reply(False, error="EXECUTION_ADAPTER_PENDING", user_id=user_id, execution_enabled=False, withdrawals_enabled=False))
            return
        self.send_json(404, reply(False, error="not_found"))


def run() -> None:
    ThreadingHTTPServer((HOST, PORT), RemoteHandler).serve_forever()


if __name__ == "__main__":
    run()
