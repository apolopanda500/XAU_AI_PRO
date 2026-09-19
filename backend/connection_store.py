"""Armazenamento local de credenciais protegido pelo Windows DPAPI."""
from __future__ import annotations
import base64, ctypes, json, os
from pathlib import Path

_CRYPTPROTECT = 0x1
class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

def _protect(value: str) -> str:
    raw = value.encode(); src = _Blob(len(raw), (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)); out = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(src), None, None, None, None, _CRYPTPROTECT, ctypes.byref(out)): raise OSError("DPAPI ProtectData falhou")
    try: return base64.b64encode(ctypes.string_at(out.pbData, out.cbData)).decode()
    finally: ctypes.windll.kernel32.LocalFree(out.pbData)

def _unprotect(value: str) -> str:
    raw = base64.b64decode(value); src = _Blob(len(raw), (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)); out = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)): raise OSError("DPAPI UnprotectData falhou")
    try: return ctypes.string_at(out.pbData, out.cbData).decode()
    finally: ctypes.windll.kernel32.LocalFree(out.pbData)

def _path() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home())) / "XAU AI PRO"; root.mkdir(parents=True, exist_ok=True); return root / "connections.dpapi.json"

def save_connection(connection_id: str, broker: str, market: str, api_key: str, api_secret: str) -> None:
    data = {}
    path = _path()
    if path.exists(): data = json.loads(path.read_text(encoding="utf-8"))
    data[connection_id] = {"broker": broker, "market": market, "api_key": _protect(api_key), "api_secret": _protect(api_secret)}
    path.write_text(json.dumps(data), encoding="utf-8")

def list_connections() -> list[dict[str, str]]:
    path = _path()
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding="utf-8")); return [{"id": k, "broker": v.get("broker", ""), "market": v.get("market", ""), "configured": True, "active": v.get("active", True)} for k, v in data.items()]

def load_credentials(broker: str, market: str) -> tuple[str, str] | None:
    path = _path()
    if not path.exists(): return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data.values():
        if item.get("broker") == broker and item.get("market") == market and item.get("active", True):
            return _unprotect(item["api_key"]), _unprotect(item["api_secret"])
    return None

def load_connection_credentials(connection_id: str) -> tuple[str, str]:
    """Obtém exatamente a conexão solicitada, sem expor segredos na listagem."""
    path = _path()
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    item = data.get(connection_id)
    if not item:
        raise LookupError("Conexão não encontrada.")
    return _unprotect(item["api_key"]), _unprotect(item["api_secret"])


def delete_connection(connection_id: str) -> bool:
    path = _path()
    if not path.exists(): return False
    data = json.loads(path.read_text(encoding="utf-8")); existed = connection_id in data; data.pop(connection_id, None); path.write_text(json.dumps(data), encoding="utf-8"); return existed

def set_connection_active(connection_id: str, active: bool) -> bool:
    path = _path()
    if not path.exists(): return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if connection_id not in data: return False
    data[connection_id]["active"] = bool(active); path.write_text(json.dumps(data), encoding="utf-8"); return True
