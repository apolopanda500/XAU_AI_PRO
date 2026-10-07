"""Cadastro e validacao de conexoes por consultas de LEITURA, sem enviar ordens.

POR QUE ESTE MODULO MUDOU (2026-09-30)
=====================================
Antes a lista de corretoras vivia em codigo, repetida tres vezes:

    if broker not in {"binance", "mexc", "bybit", "okx"}            # save()
    if item["broker"] not in {"mexc", "binance", "bybit", "okx"}    # action()
    if/elif/elif/else escolhendo o cliente                           # action()

E o MT5 era a excecao escrita a mao: "MT5 usa a sessao do terminal; nao
cadastre API key para MT5". Isso e o oposto da regra do projeto - nenhuma
corretora pode ser caminho exclusivo. MT5 nao e um caso especial: e uma
FONTE DE CREDENCIAL diferente das demais, e o modulo passa a tratar todas
pelo mesmo caminho, deixando a diferenca declarada em vez de implicita.

Agora:
- a lista vem de `broker_registry.BROKERS` (9 corretoras), nao de um set local;
- o cliente e um REGISTRO (`CLIENTES`), nao uma cadeia if/elif/else;
- MT5 entra no fluxo de listar/sincronizar como as outras, e a diferenca
  ("credencial vem da sessao do terminal") e um dado, nao um raise.

SEGURANCA
=========
Nada aqui envia ordem, e nada aqui enxerga saque ou transferencia. A
validacao e sempre `client.account()`, que e leitura. `read_only: True` no
retorno nao e decoracao: e o contrato desta camada.
"""
from __future__ import annotations

from typing import Any, Callable

from backend import connection_store as store
from backend.binance_client import BinanceClient
from backend.bybit_client import BybitClient
from backend.mexc_client import MexcClient
from backend.okx_client import OkxClient

#: Corretoras que autenticam por API key. MT5 NAO esta aqui - e o unico motivo
#: de a lista existir: a fonte da credencial e diferente. A lista de quais
#: corretoras EXISTEM vem de `broker_registry`; esta e so sobre credencial.
CLIENTES: dict[str, Callable[..., Any]] = {
    "binance": BinanceClient,
    "mexc": MexcClient,
    "bybit": BybitClient,
    "okx": OkxClient,
}

#: Corretora cuja credencial vem da sessao do terminal, e nao de API key.
#: Declarar aqui e o que permite ao resto do codigo tratar MT5 como as demais
#: em vez de um `if broker == "mt5"` espalhado.
CORRETORA_POR_SESSAO = "mt5"

#: Corretora que exige `api_passphrase` alem de key e secret. O campo existe
#: no payload e no schema; so a OKX recusa sem ele.
EXIGE_PASSPHRASE: frozenset[str] = frozenset({"okx"})


def _credencial_exigida(broker: str) -> bool:
    """True quando a corretora usa API key; False quando usa sessao do terminal."""
    return broker in CLIENTES


def _rotulo(broker: str) -> str:
    from backend.broker_registry import get_broker

    definicao = get_broker(broker)
    return definicao.label if definicao else broker


def _normaliza_market(market: str) -> str:
    from backend.broker_registry import normalize_market

    return normalize_market(market)


def save(payload: dict) -> dict:
    """Cadastra uma conexao. Nao envia ordem, so grava."""
    return _gravar(payload, criar=True)


def update(payload: dict) -> dict:
    """Troca a credencial de uma conexao que JA EXISTE. Nao envia ordem.

    POR QUE ISTO EXISTE (05/10/2026)
    ===============================
    A tela so sabia CRIAR conexao. Trocar a chave significava: excluir a
    conexao e cadastrar outra com o mesmo nome. No meio disso a conta fica
    sem credencial, e se o cadastro novo falhasse (passphrase errada, mercado
    diferente) o cliente ficava com a conexao excluida e sem chave nenhuma.

    Aqui o mesmo `id` e reescrito, entao nunca existe um instante sem
    credencial gravada.

    CORRETORA E MERCADO VEM DO REGISTRO
    ====================================
    O `id` e `broker:market:nome`, e o proprio registro gravado tem
    `broker` e `market`. Na edicao eles NAO vem do corpo da requisicao: um
    corpo incompleto faria o update recusar com "escolha a corretora", que e
    uma pergunta que o cliente nao pode responder — ele esta trocando a
    CHAVE, nao escolhendo corretora.

    Se o corpo trouxer `market` diferente do gravado, a troca e de mercado e
    nao de credencial, e a conexao nao existia com essa combinacao: recusa.
    A troca de mercado fica com o cadastro, que ja aceita reescrever o
    registro.

    CAMPO EM BRANCO = MANTER
    ==========================
    Ler de volta a chave para trocar outra exigiria devolver o segredo pela
    API — o que a listagem nunca faz, e com razao. Entao campo ausente ou em
    branco significa "mantem o que ja esta gravado". A consequence importante:
    `api_key` sozinho troca so a chave, e `api_secret` sozinho troca so o
    secret. Trocar os dois e o caminho normal.
    """
    if not isinstance(payload, dict):
        raise ValueError("Informe um objeto de conexao.")
    nome = str(payload.get("id", "")).strip()
    if not nome:
        raise ValueError("Informe a conexao a atualizar.")
    gravada = next((item for item in store.list_connections() if item["id"] == nome), None)
    if gravada is None:
        raise LookupError("Conexao nao encontrada.")
    mercado_pedido = str(payload.get("market", "")).strip()
    if mercado_pedido and _normaliza_market(mercado_pedido) != gravada["market"]:
        raise ValueError(
            "O mercado de uma conexao existente nao muda na troca de chave. "
            "Exclua a conexao e cadastre outra com o mercado desejado."
        )
    return _gravar(
        {**payload, "broker": gravada["broker"], "market": gravada["market"]},
        criar=False,
    )


def _gravar(payload: dict, *, criar: bool) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Informe um objeto de conexao.")
    from backend.broker_registry import get_broker

    broker = str(payload.get("broker", "")).strip().lower()
    if not broker:
        raise ValueError("Escolha a corretora. Nenhuma corretora e o padrao.")
    definicao = get_broker(broker)
    if definicao is None:
        raise ValueError(f"Corretora desconhecida: {broker}")
    if definicao.status not in {"active", "code_only"}:
        raise ValueError(f"{definicao.label} ainda nao esta disponivel.")

    nome = str(payload.get("id", "")).strip()
    if not nome:
        raise ValueError("De um nome a conexao.")

    market = _normaliza_market(str(payload.get("market", "")).strip())
    if market not in definicao.markets:
        raise ValueError(
            f"{definicao.label} nao opera em '{market}'. "
            f"Mercados desta corretora: {', '.join(definicao.markets)}"
        )

    if not _credencial_exigida(broker):
        # Corretora de sessao: a credencial nao vem do formulario. Registrar e
        # valido - e o que mantem MT5 no mesmo fluxo das outras.
        store.save_connection(nome, broker, market, "", "", "")
        return {
            "ok": True,
            "validated": False,
            "credential_source": "session",
            "label": definicao.label,
            "updated": criar,
        }

    key = str(payload.get("api_key", "") or "").strip()
    secret = str(payload.get("api_secret", "") or "").strip()
    passphrase = str(payload.get("api_passphrase", "") or "").strip()

    if not criar:
        # Sem o que gravar, o PUT e um no-op. Responder 200 aqui seria dizer
        # "atualizado" sem ter atualizado nada.
        if not any((key, secret, passphrase)):
            raise ValueError("Informe a nova credencial. Campo em branco mantem a atual.")
        # Na edicao, o que falta no payload vem do DPAPI. Um PUT so com `api_key`
        # troca a chave e preserva o secret — e o que permite rotacionar sem
        # digitar tudo de novo.
        chave_antiga, secret_antigo, passphrase_antiga = _credencial_atual(nome)
        key = key or chave_antiga
        secret = secret or secret_antigo
        passphrase = passphrase or passphrase_antiga

    if not key or not secret:
        raise ValueError(f"{definicao.label}: informe API key e secret.")
    if broker in EXIGE_PASSPHRASE and not passphrase:
        raise ValueError(f"{definicao.label} exige a passphrase criada junto com a API key.")

    store.save_connection(nome, broker, market, key, secret, passphrase)
    return {
        "ok": True,
        "validated": False,
        "credential_source": "api_key",
        "label": definicao.label,
        "updated": not criar,
    }


def _credencial_atual(connection_id: str) -> tuple[str, str, str]:
    """Credencial ja gravada, para completar o que o PUT nao trouxe.

    Falha aqui devolve vazio — e a troca vai recusar com "informe API key e
    secret", que e a resposta honesta. Engolir KeyError e gravar vazio por
    cima da credencial existente deixaria o cliente sem chave e sem aviso.
    """
    try:
        return store.load_connection_credentials_full(connection_id)
    except (LookupError, OSError, ValueError):
        return "", "", ""


def action(connection_id: str, command: str) -> dict:
    """Testar, ativar ou desativar uma conexao. Sempre por leitura."""
    if command not in {"test", "activate", "deactivate"}:
        raise LookupError("Comando de conexao nao encontrado.")
    item = next((row for row in store.list_connections() if row["id"] == connection_id), None)
    if item is None:
        raise LookupError("Conexao nao encontrada.")

    if command == "deactivate":
        store.set_connection_active(connection_id, False)
        return {"ok": True, "active": False, "label": _rotulo(item["broker"])}

    broker = str(item["broker"]).lower()
    if not _credencial_exigida(broker):
        # Corretora de sessao: o que se valida e a sessao, nao a API key.
        from backend.mt5_gateway import _payload

        dados = _payload()
        if not dados.get("terminal_connected"):
            raise ValueError(
                f"{_rotulo(broker)} nao esta com o terminal aberto e logado. "
                "Abra o terminal e tente de novo."
            )
        conta = dados.get("account") or {}
        if command == "activate":
            store.set_connection_active(connection_id, True)
        return {
            "ok": True,
            "validated": True,
            "read_only": True,
            "credential_source": "session",
            "label": _rotulo(broker),
            "login": conta.get("login"),
            "server": conta.get("server"),
        }

    key, secret, passphrase = store.load_connection_credentials_full(connection_id)
    market = "futures" if item["market"] == "crypto-futures" else "spot"
    cliente = CLIENTES[broker](market)
    # Os quatro clientes nomeiam os campos de credencial de jeitos diferentes
    # (`api_key`/`secret`, `api_key`/`api_secret`, mais `passphrase` na OKX).
    # Em vez de uma cadeia if/elif, atribui os que o cliente aceita.
    valores = {"api_key": key, "secret": secret, "api_secret": secret, "passphrase": passphrase}
    for campo, valor in valores.items():
        try:
            setattr(cliente, campo, valor)
        except AttributeError:
            continue
    result = cliente.account()
    if not isinstance(result, (dict, list)) or (isinstance(result, dict) and result.get("success") is False):
        raise ValueError(f"Resposta invalida de {_rotulo(broker)}.")
    if command == "activate":
        store.set_connection_active(connection_id, True)
    return {
        "ok": True,
        "validated": True,
        "read_only": True,
        "credential_source": "api_key",
        "label": _rotulo(broker),
    }
