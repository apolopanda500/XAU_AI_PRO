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

def protect_secret(value: str) -> str:
    """Envelope DPAPI de um segredo. Publico para quem guarda credencial fora
    deste store (o login automatico do MT5 usa o mesmo envelope)."""
    return _protect(value)


def unprotect_secret(value: str) -> str:
    return _unprotect(value)


def _path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "XAU AI PRO" / "connections.dpapi.json"


def _prepare_path() -> Path:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_connection(connection_id: str, broker: str, market: str, api_key: str, api_secret: str, api_passphrase: str = "") -> None:
    """Grava uma conexao. Credencial vazia e legitima para corretora de sessao.

    Corretoras que autenticam pela sessao do terminal (MT5) nao tem API key.
    Antes elas nem passavam por aqui — a conexao MT5 vivia fora deste store —
    e a validacao recusava credencial vazia. Agora que MT5 entra no mesmo
    fluxo, gravar string vazia no DPAPI seria gasto e mentira: o arquivo
    diria ter uma credencial que nao existe.

    Por isso o campo so e gravado quando tem conteudo, e a listagem diz
    `credential_source` para a interface nao pedir o que nao existe.
    """
    if not all(isinstance(value, str) and value.strip() for value in (connection_id, broker, market)):
        raise ValueError("connection_id, broker e market sao obrigatorios")
    data = {}
    path = _prepare_path()
    if path.exists(): data = json.loads(path.read_text(encoding="utf-8"))
    previous = data.get(connection_id, {})
    record = {"broker": broker, "market": market, "active": previous.get("active", True), "credential_source": "api_key" if api_key.strip() else "session"}
    for campo, valor in (("api_key", api_key), ("api_secret", api_secret), ("api_passphrase", api_passphrase)):
        if isinstance(valor, str) and valor.strip():
            record[campo] = _protect(valor.strip())
    data[connection_id] = record
    temp = path.with_suffix(".dpapi.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)

def list_connections() -> list[dict[str, object]]:
    path = _path()
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding="utf-8"))
    saida = []
    for chave, registro in data.items():
        linha = {
            "id": chave,
            "broker": registro.get("broker", ""),
            "market": registro.get("market", ""),
            "configured": bool(registro.get("api_key")),
            "active": registro.get("active", True),
        }
        # `credential_source` diz a interface o que pedir: sem ele, a tela
        # mostraria campo de API key para uma conexao que nao tem.
        linha["credential_source"] = registro.get("credential_source") or (
            "api_key" if registro.get("api_key") else "session"
        )
        saida.append(linha)
    return saida


def resolve_connection(account_id: str, broker: str, market: str) -> dict[str, object]:
    """Acha a conexao ativa de uma corretora e mercado.

    CORRETORA DE SESSAO (MT5) IGNORA O MERCADO GRAVADO
    -------------------------------------------------
    MEDIDO em 22/10/2026: duas conexoes MT5 ativas, ambas gravadas como
    `market=forex` (a tela pede um market ao cadastrar, e o operador escolhe
    forex). XAUUSD e `metal` na hierarquia da corretora, e o motor chamava
    `resolve_connection("", "mt5", "metals")` — 0 matches, LookupError, e o
    ciclo morria antes de enviar. O sintoma era "conexao ativa nao
    encontrada" para uma conta que existia e estava logada.

    A credencial de uma corretora de sessao e o TERMINAL LOGADO, e o terminal
    serve todos os mercados da corretora (forex, metals, indices, ...). O
    `market` gravado na conexao e o rotulo do que o operador escolheu ao
    cadastrar, nao um filtro de acesso. Por isso, para `credential_source ==
    "session"`, o mercado nao participa do match — so o broker e o estado
    ativo.

    Para corretora de API key (binance, mexc, bybit, okx) o mercado CONTINUA
    sendo filtro: spot e futuros sao endpoints diferentes, com permissões e
    riscos diferentes.
    """
    normalized_broker = str(broker or "").strip().lower()
    normalized_market = str(market or "").strip().lower()
    matches = [
        item for item in list_connections()
        if item["broker"].lower() == normalized_broker
        and bool(item.get("active", True))
        and (
            # Sessao: o terminal serve todos os mercados; o rotulo gravado
            # nao e filtro.
            str(item.get("credential_source", "")) == "session"
            # API key: spot e futuros sao mundos diferentes.
            or item["market"].lower() == normalized_market
        )
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
    # Corretora de sessao nao tem credencial gravada. Devolver vazio e o
    # resultado correto; o chamador (`connection_service.action`) nem chega
    # aqui para essas, porque valida pela sessao do terminal.
    if not item.get("api_key"):
        return "", "", ""
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
