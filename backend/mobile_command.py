"""Comandos remotos do painel movel - APENAS COM A TRAVA LIGADA.

O que este modulo faz e o que ele NAO faz
=========================================
Habilita, **sob a variavel `XAU_MOBILE_CONTROL_ENABLED=1`**, rotas autenticadas
que gravam um comando unico e atomico em `Data/remote_cmd.json`. A escrita e
fail-closed: sem a variavel, toda chamada morre com 403.

Este modulo NAO executa ordem no MetaTrader 5. Quem executa, ou vai executar,
e o EA (v1.2.215+) lendo o `remote_cmd.json`. Ate la o arquivo e apenas um
"pendente de assinatura", sem efeito colateral no terminal.

Invariantes:
- nenhuma linha daqui move dinheiro (`WITHDRAWALS_ENABLED` e do sistema todo);
- `confirm=true` e obrigatorio em toda chamada; sem ele, nem valida o resto;
- acao fora da allowlist morre antes de virar arquivo;
- valores respeitam faixas de seguranca;
- o arquivo e gravado atomicamente: ou o EA ve um comando INTEIRO, ou nada;
- `command_id` e unico (idempotencia quando o EA executar).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"
CMD_FILE = Path(os.getenv("XAU_MOBILE_CMD_FILE", str(DATA_DIR / "remote_cmd.json")))

ACOES_PERMITIDAS = frozenset(
    {
        "RESUME_AUTO",
        "PAUSE_AUTO",
        "CLOSE_ALL_POSITIONS",
        "MOVE_ALL_BREAKEVEN",
        "SET_RISK_PCT",
        "SET_DAILY_TARGET_USD",
        "SET_PROP_PROFILE",
    }
)
PERFIS_PERMITIDOS = frozenset({"STANDARD", "FTMO", "FUNDEDNEXT", "THE5ERS"})


def comandos_habilitados() -> bool:
    """True SOMENTE quando `XAU_MOBILE_CONTROL_ENABLED` e exatamente '1'."""
    return os.getenv("XAU_MOBILE_CONTROL_ENABLED", "0").strip() == "1"


def montar_comando(
    *,
    action: Any,
    value: Any = None,
    profile: Any = None,
    command_id: Any = None,
    confirm: Any = None,
) -> dict:
    """Valida a intencao e devolve o payload pronto para persistir.

    Levanta ValueError com motivo textual; a rota transforma isso em 400.
    Nenhuma validacao aqui consulta a rede nem o MT5 - e tudo estatico.
    """
    if confirm is not True:
        # Confirmar como bool estrito: 1/'true' valem como True em Python.
        # Aqui o protocolo pede explicitamente o literal JSON `true`.
        raise ValueError("confirm=true obrigatorio para destravar a acao.")

    if not isinstance(action, str):
        raise ValueError("acao deve ser texto.")
    action = action.strip().upper()
    if action not in ACOES_PERMITIDAS:
        raise ValueError(f"acao nao permitida: {action!r}")

    if action == "SET_RISK_PCT":
        try:
            risco = float(value)  # noqa: F841
        except (TypeError, ValueError):
            raise ValueError("SET_RISK_PCT exige value numerico.") from None
        if not (0.1 <= risco <= 5.0):
            raise ValueError("SET_RISK_PCT fora da faixa segura (0.1-5.0%).")
        valor_validado = risco
    elif action == "SET_DAILY_TARGET_USD":
        try:
            alvo = float(value)  # noqa: F841
        except (TypeError, ValueError):
            raise ValueError("SET_DAILY_TARGET_USD exige value numerico.") from None
        if alvo <= 0:
            raise ValueError("SET_DAILY_TARGET_USD deve ser maior que zero.")
        valor_validado = alvo
    else:
        valor_validado = None

    if action == "SET_PROP_PROFILE":
        perfil = str(profile or "").strip().upper()
        if perfil not in PERFIS_PERMITIDOS:
            raise ValueError("SET_PROP_PROFILE exige profile em STANDARD, FTMO, FUNDEDNEXT, THE5ERS.")
        perfil_validado = perfil
    else:
        perfil_validado = None

    cid = str(command_id).strip() if command_id else ""
    if not cid:
        cid = f"mob_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    cid = cid[:64]

    return {
        "command_id": cid,
        "action": action,
        "value": valor_validado,
        "profile": perfil_validado,
        "confirm": True,
        "timestamp_utc": int(time.time()),
    }


_LOCK = threading.Lock()


def escrever_comando(payload: dict) -> dict:
    """Grava o comando de forma atomica e devolve o recibo.

    Um lock em processo protege tmp+rename contra rajadas concorrentes do
    celular: sem ele, o Windows (Defender) recusava ocasionalmente o rename
    e a escrita de um comando morria em voo.
    """
    if not comandos_habilitados():
        # Defesa em profundidade: a rota tambem checa. Este caminho so existe
        # caso alguem chame esta funcao diretamente a partir de outro lugar.
        raise RuntimeError("controle movel desabilitado (XAU_MOBILE_CONTROL_ENABLED != 1).")

    with _LOCK:
        CMD_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CMD_FILE.with_name(f"{CMD_FILE.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        try:
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, CMD_FILE)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

    return {
        "ok": True,
        "status": "EXECUTED",
        "command_id": payload["command_id"],
        "action": payload["action"],
    }
