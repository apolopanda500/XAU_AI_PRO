"""Central de comando movel - SOMENTE LEITURA.

O QUE ESTE MODULO E (E O QUE ELE NAO E)
=======================================
Este modulo monta o retrato que a tela movel mostra: conta, posicoes, ordens
pendentes, saude do gateway e limites de risco. Ele **nao executa nada**:
nao envia ordem, nao fecha posicao, nao altera stop, nao libera saque.

Por que a linha e dura e nao "configuravel"
-------------------------------------------
MEDIDO no projeto: a tela do celular e o caminho mais curto entre um toque
acidental (bolso, tela molhada, dedo no lugar errado) e uma ordem real. O
gateway ja tem `THIRD_PARTY_READ_ONLY` e fail-closed por token; um modulo movel
que ganhasse rota de escrita furaria as duas guardas por fora, porque ele fala
com o gateway ja autenticado. Portanto:

- `READ_ONLY = True` e constante, nao input;
- `COMMANDS_ENABLED = False` e constante, nao input;
- `WITHDRAWALS_ENABLED = False` e constante (AGENTS.md SS2: nunca sai dinheiro);
- nao existe funcao que aceite `confirm=True` nem `execute=True`.

Um controle que nada le e pior que a ausencia dele (AGENTS.md SS9). Por isso
cada bloco do payload diz `ok` e `motivo`: ausencia de dado e RECUSA COM
MOTIVO, nunca zero silencioso.

REGRA DO SIMBOLO (AGENTS.md SS3)
--------------------------------
Simbolo vazio e recusa com motivo. Nao existe ativo padrao, nem "XAUUSD como
fallback": uma lista fixa contra os milhares de simbolos da corretora e
exatamente a presuncao que a regra proibe.

SEGREDO NAO ENTRA NO PAYLOAD (AGENTS.md SS12)
---------------------------------------------
`_segredos()` varre o payload montado e denuncia qualquer chave com nome de
credencial. A varredura roda no autoteste, entao um campo novo chamado
`token`/`senha`/`api_key` reprova antes de sair do repositorio.
"""
from __future__ import annotations

import json
from time import time
from typing import Any, Iterable, Mapping

# ---------------------------------------------------------------------------
# Constantes de seguranca. Nao viram input em nenhum ponto deste modulo.
# ---------------------------------------------------------------------------
READ_ONLY = True
COMMANDS_ENABLED = False
EXECUTION_ENABLED = False
WITHDRAWALS_ENABLED = False

# Nomes de chave que NUNCA podem aparecer no payload (comparados em minusculas,
# por substring: `xau_api_key`, `gatewayToken` e `authorization` caem todos).
_CAMPOS_PROIBIDOS = (
    "token",
    "password",
    "senha",
    "secret",
    "segredo",
    "api_key",
    "apikey",
    "authorization",
    "dsn",
    "cookie",
    "private_key",
)

# Lateralidades que o MT5 entrega em `type` (0/1) e as formas textuais que
# outros adaptadores usam. O que nao esta no mapa NAO e adivinhado: vira
# "desconhecido", porque rotular uma venda como compra e pior que nao rotular.
_LADOS = {
    "0": "compra",
    "buy": "compra",
    "compra": "compra",
    "long": "compra",
    "1": "venda",
    "sell": "venda",
    "venda": "venda",
    "short": "venda",
    # Tipos de ORDEM PENDENTE do MT5 (ORDER_TYPE_BUY_LIMIT..SELL_STOP_LIMIT).
    # Sem eles a ordem pendente aparecia como "lado nao informado" mesmo tendo
    # lado definido no terminal. 2/4/6 abrem compra; 3/5/7 abrem venda.
    "2": "compra",
    "4": "compra",
    "6": "compra",
    "3": "venda",
    "5": "venda",
    "7": "venda",
}


# ---------------------------------------------------------------------------
# Utilitarios de leitura. Nenhum deles levanta excecao: a tela movel precisa
# mostrar "o campo X nao veio", nao uma tela branca.
# ---------------------------------------------------------------------------
def _numero(valor: Any, padrao: float | None = None) -> float | None:
    """Converte para float finito. NaN/inf/bool viram `padrao`."""
    if isinstance(valor, bool):
        # `bool` e subclasse de `int` em Python: sem esta linha, True viraria 1.0
        # e um `ok` booleano apareceria como saldo.
        return padrao
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    if numero != numero or numero in (float("inf"), float("-inf")):
        return padrao
    return numero


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _primeiro(bruto: Mapping[str, Any], *nomes: str) -> Any:
    """Primeiro campo presente e nao vazio. O nome difere entre adaptadores
    (`symbol`/`simbolo`, `volume`/`quantity`) - AGENTS.md SS5."""
    for nome in nomes:
        if nome in bruto:
            valor = bruto[nome]
            if valor is None:
                continue
            if isinstance(valor, str) and not valor.strip():
                continue
            return valor
    return None


def _segredos(dado: Any, caminho: str = "") -> list[str]:
    """Caminhos do payload cujo NOME parece credencial. Le o nome, nunca o valor."""
    achados: list[str] = []
    if isinstance(dado, Mapping):
        for chave, valor in dado.items():
            nome = str(chave).lower()
            aqui = f"{caminho}.{chave}" if caminho else str(chave)
            if any(proibido in nome for proibido in _CAMPOS_PROIBIDOS):
                achados.append(aqui)
                continue  # nao desce no valor: o achado ja basta
            achados.extend(_segredos(valor, aqui))
    elif isinstance(dado, (list, tuple)):
        for indice, valor in enumerate(dado):
            achados.extend(_segredos(valor, f"{caminho}[{indice}]"))
    return achados


# ---------------------------------------------------------------------------
# Blocos do retrato
# ---------------------------------------------------------------------------
def resumo_conta(conta: Mapping[str, Any] | None) -> dict:
    """Identidade e saldo da conta ativa.

    `login` e `servidor` sao obrigatorios: sem eles o operador nao sabe QUAL
    conta esta olhando, e um saldo sem dono e pior que saldo nenhum.
    """
    if not isinstance(conta, Mapping) or not conta:
        return {
            "ok": False,
            "motivo": "conta nao informada pelo terminal",
            "login": None,
            "servidor": "",
            "corretora": "",
            "moeda": "",
            "saldo": None,
            "equity": None,
            "margem_livre": None,
            "alavancagem": None,
        }

    login = _primeiro(conta, "login", "account", "conta")
    servidor = _texto(_primeiro(conta, "server", "servidor"))
    saldo = _numero(_primeiro(conta, "balance", "saldo"))
    equity = _numero(_primeiro(conta, "equity", "patrimonio"))

    motivo = ""
    if login is None:
        motivo = "conta sem login"
    elif not servidor:
        motivo = "conta sem servidor: nao da para saber qual terminal respondeu"

    return {
        "ok": motivo == "",
        "motivo": motivo,
        "login": login,
        "servidor": servidor,
        "corretora": _texto(_primeiro(conta, "broker", "corretora", "company")),
        "moeda": _texto(_primeiro(conta, "currency", "moeda")),
        "saldo": saldo,
        "equity": equity,
        "margem_livre": _numero(_primeiro(conta, "margin_free", "margem_livre", "free_margin")),
        "alavancagem": _numero(_primeiro(conta, "leverage", "alavancagem")),
    }


def _item_posicao(bruta: Mapping[str, Any]) -> dict:
    """Normaliza UMA posicao. Campo ausente fica `None`; nunca vira zero."""
    lado_bruto = _texto(_primeiro(bruta, "type", "side", "lado", "tipo")).lower()
    volume = _numero(_primeiro(bruta, "volume", "quantity", "lots", "lote"))
    return {
        "ticket": _primeiro(bruta, "ticket", "id", "position_id"),
        "simbolo": _texto(_primeiro(bruta, "symbol", "simbolo")),
        "lado": _LADOS.get(lado_bruto, "desconhecido"),
        "volume": None if volume is None else abs(volume),
        "preco_abertura": _numero(_primeiro(bruta, "price_open", "open_price", "preco_abertura")),
        "preco_atual": _numero(_primeiro(bruta, "price_current", "current_price", "preco_atual")),
        "stop_loss": _numero(_primeiro(bruta, "sl", "stop_loss")),
        "take_profit": _numero(_primeiro(bruta, "tp", "take_profit")),
        "lucro": _numero(_primeiro(bruta, "profit", "lucro", "pnl")),
        "comentario": _texto(_primeiro(bruta, "comment", "comentario")),
    }


def resumo_posicoes(posicoes: Iterable[Any] | None, disponivel: bool = True) -> dict:
    """Posicoes abertas. Cada linha sem simbolo e RECUSADA com motivo (SS3).

    `disponivel=False` e o caso que parece "sem posicao" e nao e: o terminal
    nao respondeu. Lista vazia por falha de leitura e lista vazia de verdade
    sao a mesma tela se ninguem disser a diferenca - e o operador abre ordem
    achando que esta zerado.
    """
    if not disponivel:
        return {
            "ok": False,
            "disponivel": False,
            "motivo": "posicoes indisponiveis: o terminal MT5 nao respondeu",
            "total": 0,
            "lidos": 0,
            "recusadas": 0,
            "itens": [],
        }
    itens: list[dict] = []
    recusas: list[str] = []
    total = 0
    for bruta in posicoes or []:
        total += 1
        if not isinstance(bruta, Mapping):
            recusas.append(f"posicao #{total} em formato inesperado")
            continue
        item = _item_posicao(bruta)
        if not item["simbolo"]:
            recusas.append(f"posicao {item['ticket'] or '#' + str(total)} sem simbolo")
            continue
        itens.append(item)
    return {
        "ok": not recusas,
        "disponivel": True,
        "motivo": "; ".join(recusas),
        "total": len(itens),
        "lidos": total,
        "recusadas": len(recusas),
        "itens": itens,
    }


def resumo_ordens(ordens: Iterable[Any] | None, disponivel: bool = True) -> dict:
    """Ordens pendentes. Mesma regra: sem simbolo, recusa com motivo."""
    if not disponivel:
        return {
            "ok": False,
            "disponivel": False,
            "motivo": "ordens pendentes indisponiveis: o terminal MT5 nao respondeu",
            "total": 0,
            "recusadas": 0,
            "itens": [],
        }
    itens: list[dict] = []
    recusas: list[str] = []
    for indice, bruta in enumerate(ordens or [], start=1):
        if not isinstance(bruta, Mapping):
            recusas.append(f"ordem #{indice} em formato inesperado")
            continue
        simbolo = _texto(_primeiro(bruta, "symbol", "simbolo"))
        if not simbolo:
            recusas.append(f"ordem #{indice} sem simbolo")
            continue
        itens.append(
            {
                "ticket": _primeiro(bruta, "ticket", "id", "order_id"),
                "simbolo": simbolo,
                "lado": _LADOS.get(
                    _texto(_primeiro(bruta, "type", "side", "lado", "tipo")).lower(),
                    "desconhecido",
                ),
                "volume": _numero(_primeiro(bruta, "volume_current", "volume", "lote")),
                "preco": _numero(_primeiro(bruta, "price_open", "price", "preco")),
                "stop_loss": _numero(_primeiro(bruta, "sl", "stop_loss")),
                "take_profit": _numero(_primeiro(bruta, "tp", "take_profit")),
            }
        )
    return {
        "ok": not recusas,
        "disponivel": True,
        "motivo": "; ".join(recusas),
        "total": len(itens),
        "recusadas": len(recusas),
        "itens": itens,
    }


def resumo_saude(saude: Mapping[str, Any] | None) -> dict:
    """Saude do gateway. `ok` aqui e o `ok` que o gateway devolveu, nao um
    `ok` inventado por ausencia de resposta."""
    if not isinstance(saude, Mapping) or not saude:
        return {
            "ok": False,
            "motivo": "gateway nao respondeu a leitura de saude",
            "gateway_build": "",
            "uptime_sec": None,
            "terminal_connected": None,
        }
    return {
        "ok": bool(saude.get("ok")) and bool(saude.get("gateway_build", True)),
        "motivo": "",
        "gateway_build": _texto(_primeiro(saude, "gateway_build", "build", "version")),
        "uptime_sec": _numero(_primeiro(saude, "uptime_sec", "uptime")),
        # O gateway no ar NAO significa terminal conectado: sao dois lados.
        # `None` = o campo nao veio, e a tela precisa dizer isso em vez de
        # pintar verde por ausencia.
        "terminal_connected": saude.get("terminal_connected")
        if isinstance(saude.get("terminal_connected"), bool)
        else None,
    }


def resumo_risco(risco: Mapping[str, Any] | None) -> dict:
    """Limites de risco e distancia ate eles. Nada aqui altera limite."""
    if not isinstance(risco, Mapping) or not risco:
        return {
            "ok": False,
            "motivo": "limites de risco nao informados",
            "risco_por_operacao_pct": None,
            "perda_diaria_pct": None,
            "perda_diaria_limite_pct": None,
            "drawdown_pct": None,
            "drawdown_limite_pct": None,
            "bloqueios": [],
        }

    perda = _numero(_primeiro(risco, "perda_diaria_pct", "daily_loss_pct"))
    perda_limite = _numero(_primeiro(risco, "perda_diaria_limite_pct", "max_daily_loss_pct"))
    dd = _numero(_primeiro(risco, "drawdown_pct", "drawdown"))
    dd_limite = _numero(_primeiro(risco, "drawdown_limite_pct", "max_drawdown_pct"))

    # Os bloqueios sao LEITURA do que ja aconteceu. O modulo nao bloqueia nada;
    # ele diz ao operador por que a IA/EA parou de abrir.
    bloqueios: list[str] = []
    if perda is not None and perda_limite is not None and perda_limite > 0 and perda >= perda_limite:
        bloqueios.append("perda diaria atingiu o limite configurado")
    if dd is not None and dd_limite is not None and dd_limite > 0 and dd >= dd_limite:
        bloqueios.append("drawdown atingiu o limite configurado")

    return {
        "ok": True,
        "motivo": "",
        "risco_por_operacao_pct": _numero(_primeiro(risco, "risco_por_operacao_pct", "risk_percent")),
        "perda_diaria_pct": perda,
        "perda_diaria_limite_pct": perda_limite,
        "drawdown_pct": dd,
        "drawdown_limite_pct": dd_limite,
        "bloqueios": bloqueios,
    }


def montar_snapshot(
    conta: Mapping[str, Any] | None = None,
    posicoes: Iterable[Any] | None = None,
    ordens: Iterable[Any] | None = None,
    saude: Mapping[str, Any] | None = None,
    risco: Mapping[str, Any] | None = None,
    agora: float | None = None,
    posicoes_disponiveis: bool = True,
    ordens_disponiveis: bool = True,
) -> dict:
    """Retrato completo, pronto para a tela movel.

    Todos os campos sao injetados: o modulo nao importa MT5, nao abre socket e
    nao le arquivo. Quem le o terminal e o gateway; aqui so se normaliza.
    """
    caixa = resumo_conta(conta)
    pos = resumo_posicoes(posicoes, disponivel=posicoes_disponiveis)
    ord = resumo_ordens(ordens, disponivel=ordens_disponiveis)
    saude_final = resumo_saude(saude)
    risco_final = resumo_risco(risco)

    avisos: list[str] = []
    for bloco_nome, bloco in (
        ("conta", caixa),
        ("posicoes", pos),
        ("ordens", ord),
        ("saude", saude_final),
        ("risco", risco_final),
    ):
        if not bloco["ok"] and bloco["motivo"]:
            avisos.append(f"{bloco_nome}: {bloco['motivo']}")

    return {
        "ok": True,  # a LEITURA funcionou; o estado de cada bloco diz o resto
        "read_only": READ_ONLY,
        "commands_enabled": COMMANDS_ENABLED,
        "execution_enabled": EXECUTION_ENABLED,
        "withdrawals_enabled": WITHDRAWALS_ENABLED,
        "gerado_em": int(time() if agora is None else agora),
        "conta": caixa,
        "posicoes": pos,
        "ordens": ord,
        "saude": saude_final,
        "risco": risco_final,
        "avisos": avisos,
        "comandos_recusados": [
            "abrir ordem",
            "fechar posicao",
            "alterar stop/take",
            "cancelar ordem",
            "saque ou transferencia",
        ],
    }


def montar_de_leitura(
    bruto: Mapping[str, Any] | None,
    saude: Mapping[str, Any] | None = None,
    risco: Mapping[str, Any] | None = None,
    erros: Iterable[Any] | None = None,
) -> dict:
    """Converte a leitura CRUA do gateway no retrato da tela movel.

    Existe separado da rota para o teste exercitar o caminho de verdade: o
    teste importa esta funcao e passa o mesmo formato que `gw._payload()` e
    `gw._status_snapshot()` devolvem. Um teste que copiasse o mapeamento
    provaria que a copia esta certa - AGENTS.md SS6.
    """
    leitura = bruto if isinstance(bruto, Mapping) else {}
    avisos_extras = [str(e).strip() for e in (erros or []) if str(e).strip()]

    posicoes = leitura.get("positions")
    posicoes_disponiveis = leitura.get("positions_available") is True
    if not isinstance(posicoes, list):
        if posicoes_disponiveis:
            avisos_extras.append("positions veio em formato inesperado")
        posicoes = []
        posicoes_disponiveis = False

    ordens = leitura.get("pending_orders")
    ordens_disponiveis = leitura.get("pending_orders_available") is True
    if not isinstance(ordens, list):
        if ordens_disponiveis:
            avisos_extras.append("pending_orders veio em formato inesperado")
        ordens = []
        ordens_disponiveis = False

    corpo = montar_snapshot(
        conta=leitura.get("account"),
        posicoes=posicoes,
        ordens=ordens,
        saude=saude,
        risco=risco,
        posicoes_disponiveis=posicoes_disponiveis,
        ordens_disponiveis=ordens_disponiveis,
    )
    corpo["avisos"].extend(avisos_extras)
    return corpo


# ---------------------------------------------------------------------------
# Autoteste. Roda com `python -m backend.mobile_control` e reprova (exit 1)
# quando a guarda quebrar. Prova negativa obrigatoria (AGENTS.md SS6).
# ---------------------------------------------------------------------------
def autoteste() -> list[str]:
    falhas: list[str] = []

    def checar(condicao: bool, mensagem: str) -> None:
        if not condicao:
            falhas.append(mensagem)

    # 1. Vazio nao vira zero silencioso.
    vazio = montar_snapshot()
    checar(vazio["conta"]["ok"] is False, "conta vazia deveria ser recusa com motivo")
    checar(vazio["conta"]["saldo"] is None, "saldo ausente nao pode virar 0")
    checar(vazio["avisos"], "recusas precisam aparecer em `avisos`")
    checar(vazio["read_only"] is True, "read_only precisa ser True")
    checar(vazio["commands_enabled"] is False, "commands_enabled precisa ser False")
    checar(vazio["withdrawals_enabled"] is False, "withdrawals_enabled precisa ser False")

    # 2. Simbolo vazio e recusa, nunca ativo padrao.
    sem_simbolo = resumo_posicoes([{"ticket": 1, "symbol": "  ", "volume": 1.0}])
    checar(sem_simbolo["total"] == 0, "posicao sem simbolo nao pode entrar na lista")
    checar(bool(sem_simbolo["motivo"]), "posicao sem simbolo precisa de motivo")
    checar(
        not any(item.get("simbolo") for item in sem_simbolo["itens"]),
        "nenhum simbolo pode ser presumido",
    )

    # 3. Lado desconhecido nao vira compra nem venda.
    lado = _item_posicao({"symbol": "EURUSD", "type": "hedge"})
    checar(lado["lado"] == "desconhecido", "lado desconhecido nao pode ser adivinhado")

    # 4. Volume negativo (venda no MT5) entra em modulo, com o lado dizendo o resto.
    venda = _item_posicao({"symbol": "EURUSD", "type": 1, "volume": -0.5})
    checar(venda["volume"] == 0.5, "volume precisa ser absoluto")
    checar(venda["lado"] == "venda", "type=1 precisa ser venda")

    # 5. Conta sem servidor e recusa: saldo sem dono nao serve.
    sem_servidor = resumo_conta({"login": 123, "balance": 1000.0})
    checar(sem_servidor["ok"] is False, "conta sem servidor precisa recusar")
    checar("servidor" in sem_servidor["motivo"], "o motivo precisa nomear o campo")

    # 6. NaN/inf nao atravessam o JSON.
    estranho = resumo_conta({"login": 1, "server": "X", "balance": float("nan")})
    checar(estranho["saldo"] is None, "NaN precisa virar None, nao numero")

    # 7. Limite de risco atingido aparece como leitura, sem bloquear nada.
    risco = resumo_risco({"perda_diaria_pct": 3.0, "perda_diaria_limite_pct": 3.0})
    checar(bool(risco["bloqueios"]), "limite atingido precisa aparecer em `bloqueios`")

    # 8. Prova negativa do filtro de segredo: se ele nao achar nada, nao serve.
    plantado = {"conta": {"ok": True, "authorization": "Bearer x"}, "lista": [{"api_key": "y"}]}
    achados = _segredos(plantado)
    checar(len(achados) == 2, f"filtro de segredo deveria achar 2, achou {len(achados)}")

    # 9. O payload real nao contem nome de credencial.
    real = montar_snapshot(
        conta={"login": 1, "server": "S", "balance": 10.0},
        posicoes=[{"ticket": 9, "symbol": "EURUSD", "type": 0, "volume": 0.1}],
        saude={"ok": True, "gateway_build": "1.2.4"},
    )
    checar(not _segredos(real), f"payload com credencial: {_segredos(real)}")

    # 10. O payload precisa ser JSON serializavel (a tela le JSON, nao dict).
    try:
        json.dumps(real, ensure_ascii=False)
    except (TypeError, ValueError) as exc:  # pragma: no cover - guarda de tipo
        falhas.append(f"payload nao serializavel: {exc}")

    # 11. Terminal mudo NAO pode parecer conta zerada.
    mudo = montar_snapshot(
        conta={"login": 1, "server": "S"},
        posicoes=[],
        posicoes_disponiveis=False,
    )
    checar(mudo["posicoes"]["ok"] is False, "posicoes indisponiveis precisam ser recusa")
    checar(mudo["posicoes"]["disponivel"] is False, "o payload precisa declarar `disponivel`")
    checar(
        "indisponiveis" in mudo["posicoes"]["motivo"],
        "o motivo precisa dizer que o terminal nao respondeu",
    )
    checar(
        any("posicoes" in aviso for aviso in mudo["avisos"]),
        "a recusa de posicoes precisa aparecer em `avisos`",
    )

    # 12. Gateway no ar nao significa terminal conectado.
    desconectado = resumo_saude({"ok": True, "gateway": "online", "terminal_connected": False})
    checar(
        desconectado["terminal_connected"] is False,
        "terminal desconectado precisa atravessar o resumo",
    )
    sem_campo = resumo_saude({"ok": True, "gateway": "online"})
    checar(
        sem_campo["terminal_connected"] is None,
        "campo ausente precisa ser None, nunca False nem True inventado",
    )

    return falhas


if __name__ == "__main__":  # pragma: no cover
    import sys

    problemas = autoteste()
    if problemas:
        for problema in problemas:
            print(f"[X] {problema}")
        sys.exit(1)
    print("[OK] mobile_control: 12 verificacoes, somente leitura")
