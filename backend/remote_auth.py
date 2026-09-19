"""Autenticação multiusuário local/remota, sem armazenar segredos de corretoras."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path
from time import time

DB_PATH = Path(__import__("os").getenv("XAU_AUTH_DB", str(Path(__file__).with_name("auth.sqlite3"))))
SESSION_TTL = 3600


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
    db.commit()
    return db


def _password_hash(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("a senha deve ter pelo menos 12 caracteres")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _password_ok(password: str, encoded: str) -> bool:
    try:
        _, salt_hex, digest_hex = encoded.split("$")
        candidate = _password_hash(password, bytes.fromhex(salt_hex)).split("$")[-1]
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def register(email: str, password: str) -> int:
    normalized = email.strip().lower()
    if "@" not in normalized or len(normalized) > 254:
        raise ValueError("email inválido")
    with _db() as db:
        try:
            cur = db.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)", (normalized, _password_hash(password), int(time())))
            return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("usuário já cadastrado") from exc


def login(email: str, password: str) -> tuple[str, int]:
    with _db() as db:
        row = db.execute("SELECT id,password_hash FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row or not _password_ok(password, row[1]):
            raise PermissionError("credenciais inválidas")
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash, row[0], int(time()) + SESSION_TTL))
        db.commit()
        return raw, int(row[0])


def authenticate(token: str) -> int:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _db() as db:
        row = db.execute("SELECT user_id,expires_at FROM sessions WHERE token_hash=?", (token_hash,)).fetchone()
        if not row or row[1] <= int(time()):
            raise PermissionError("sessão inválida ou expirada")
        return int(row[0])


def logout(token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _db() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
        db.commit()
