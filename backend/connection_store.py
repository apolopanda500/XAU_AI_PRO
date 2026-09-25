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
    return Path(os.environ.get("APPDATA", Path.home())) / "XAU AI PRO" / "connections.dpapi.json"


def _prepare_path() -> Path:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_connection(connection_id: str, broker: str, market: str, api_key: str, api_secret: str, api_passphrase: str = "") -> None:
    if not all(isinstance(value, str) and value.strip() for value in (connection_id, broker, market, api_key, api_secret)):
        raise ValueError("connection_id, broker, market, api_key e api_secret sao obrigatorios")
    data = {}
    path = _prepare_path()
    if path.exists(): data = json.loads(path.read_text(encoding="utf-8"))
    previous = data.get(connection_id, {})
    record = {"broker": broker, "market": market, "active": previous.get("active", True), "api_key": _protect(api_key.strip()), "api_secret": _protect(api_secret.strip())}
    if isinstance(api_passphrase, str) and api_passphrase.strip():
        record["api_passphrase"] = _protect(api_passphrase.strip())
    data[connection_id] = record
    temp = path.with_suffix(".dpapi.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)

def list_connections() -> list[dict[str, object]]:
    path = _path()
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding="utf-8")); return [{"id": k, "broker": v.get("broker", ""), "market": v.get("market", ""), "configured": True, "active": v.get("active", True)} for k, v in data.items()]


def resolve_connection(account_id: str, broker: str, market: str) -> dict[str, object]:
    normalized_broker = str(broker or "").strip().lower()
    normalized_market = str(market or "").strip().lower()
    matches = [
        item for item in list_connections()
        if item["broker"].lower() == normalized_broker
        and item["market"].lower() == normalized_market
        and bool(item.get("active", True))
    ]
    requested = str(account_id or "").strip()
    if requested:
        selected = next((item for item in matches if item["id"] == requested), None)
        if selected is None:
            raise LookupError("conexão inativa ou incompatível com corretora e mercado")
        return selected
    if len(matches) > 1:
        raise LookupError("account_id é obrigatório quando há mais de uma conta ativa")
    if not matches:
        raise LookupError("conexão ativa não encontrada")
    return matches[0]


def load_connection_credentials(connection_id: str) -> tuple[str, str]:

    """Obtém exatamente a conexão solicitada, sem expor segredos na listagem."""
    key, secret, _ = load_connection_credentials_full(connection_id)
    return key, secret


def load_connection_credentials_full(connection_id: str) -> tuple[str, str, str]:
    path = _path()
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    item = data.get(connection_id)
    if not item:
        raise LookupError("Conexão não encontrada.")
    passphrase = _unprotect(item["api_passphrase"]) if item.get("api_passphrase") else ""
    return _unprotect(item["api_key"]), _unprotect(item["api_secret"]), passphrase


def delete_connection(connection_id: str) -> bool:
    path = _path()
    if not path.exists(): return False
    data = json.loads(path.read_text(encoding="utf-8")); existed = connection_id in data
    if not existed: return False
    data.pop(connection_id, None)
    # Substituicao atomica evita arquivo parcial e permite excluir conexao ativa.
    temp = path.with_suffix(".dpapi.tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp, path)
    return True

def set_connection_active(connection_id: str, active: bool) -> bool:
    path = _path()
    if not path.exists(): return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if connection_id not in data: return False
    data[connection_id]["active"] = bool(active)
    temp = path.with_suffix(".dpapi.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)
    return True
