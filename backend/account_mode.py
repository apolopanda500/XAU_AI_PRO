"""Modo da conta MT5 — fonte unica da verdade.

MEDIDO em 21/10/2026 na conta demo `113568614` (servidor `MetaQuotes-Demo`):
`account_info().trade_mode` devolveu `0`, e o codigo rotulava isso como
`REAL`. A conta e DEMO. O defeito era o MAPA, nao a conta.

O MetaTrader5 define (documentacao oficial do terminal, secao
`ACCOUNT_TRADE_MODE_*`):

    ACCOUNT_TRADE_MODE_DEMO    = 0   conta de teste
    ACCOUNT_TRADE_MODE_CONTEST = 1   conta de contestacao
    ACCOUNT_TRADE_MODE_REAL    = 2   conta com dinheiro real

O codigo antigo usava `{0: "REAL", 1: "DEMO", 2: "CONTEST"}` — exatamente
invertido nos dois primeiros casos. Um numero escrito a mao e um numero que
alguem vai ler errado: por isso as constantes vem do proprio MetaTrader5
quando ele esta instalado, e o fallback documentado existe so para o CI
Linux, onde o terminal nao existe.

Este modulo e o unico lugar do projeto que traduz `trade_mode` em rotulo.
Qualquer outro rotulo e um rotulo proprio, e um rotulo proprio divergindo
deste e o defeito que o §5 do AGENTS.md descreve.
"""

from __future__ import annotations

from typing import Any

#: Valores oficiais do MetaTrader5. Fonte: documentacao do terminal,
#: constantes `ACCOUNT_TRADE_MODE_*`. MEDIDAS no terminal instalado:
#: `MetaTrader5.ACCOUNT_TRADE_MODE_DEMO == 0`, `..._CONTEST == 1`,
#: `..._REAL == 2`.
TRADE_MODE_DEMO = 0
TRADE_MODE_CONTEST = 1
TRADE_MODE_REAL = 2

#: Rotulo -> valor numerico, no PADRAO DOCUMENTADO. Vale quando o terminal
#: nao esta presente (CI em Linux, maquina sem MT5).
ROTUOLO_PARA_MODO = {
    "DEMO": TRADE_MODE_DEMO,
    "CONTEST": TRADE_MODE_CONTEST,
    "REAL": TRADE_MODE_REAL,
}

#: Mapa valor numerico -> rotulo, no PADRAO DOCUMENTADO. Inversao do de cima.
MODO_NUMERO_PARA_ROTULO = {valor: rotulo for rotulo, valor in ROTUOLO_PARA_MODO.items()}


def _constantes_do_terminal() -> dict[str, int]:
    """Constantes ACCOUNT_TRADE_MODE_* do MetaTrader5, quando instalado.

    O terminal e a fonte da verdade. Se ele nao esta presente (CI em Linux,
    testes em maquina sem MT5), cai para os valores documentados acima - que
    sao os mesmos do terminal, medidos.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception:  # noqa: BLE001 - terminal ausente e um estado normal
        return {}
    encontrados: dict[str, int] = {}
    for nome, padrao in (
        ("ACCOUNT_TRADE_MODE_DEMO", TRADE_MODE_DEMO),
        ("ACCOUNT_TRADE_MODE_CONTEST", TRADE_MODE_CONTEST),
        ("ACCOUNT_TRADE_MODE_REAL", TRADE_MODE_REAL),
    ):
        valor = getattr(mt5, nome, None)
        if isinstance(valor, int) and not isinstance(valor, bool):
            encontrados[nome] = valor
        else:
            encontrados[nome] = padrao
    return {
        "DEMO": encontrados["ACCOUNT_TRADE_MODE_DEMO"],
        "CONTEST": encontrados["ACCOUNT_TRADE_MODE_CONTEST"],
        "REAL": encontrados["ACCOUNT_TRADE_MODE_REAL"],
    }


def modo_para_rotulo() -> dict[str, int]:
    """Mapa rotulo -> numero, lido do terminal AGORA.

    POR QUE NAO E CONSTANTE DE IMPORT: o terminal e injetado em
    sys.modules em tempo de teste, e o Tauri sobe o gateway com o terminal
    ja aberto. Um mapa fixado no import congelaria o valor do primeiro
    import e passaria a mentir para todo mundo depois disso - que e o mesmo
    formato de defeito do AGENTS.md: dois lados do mesmo dado discordando,
    com o nome certo e o valor errado.
    """
    return _constantes_do_terminal() or dict(ROTUOLO_PARA_MODO)


def modo_numero_para_rotulo() -> dict[int, str]:
    """Mapa numero -> rotulo, lido do terminal agora.

    Inverter este mapa foi exatamente o defeito original: com o mapa trocado,
    modo_da_conta(0) devolvia UNKNOWN e modo_da_conta(2) devolvia DEMO -
    trocar nomes resolve o sintoma e mantem o defeito.
    """
    return {valor: rotulo for rotulo, valor in modo_para_rotulo().items()}


def modo_da_conta(trade_mode: Any) -> str:
    """Rotulo (`DEMO`/`CONTEST`/`REAL`/`UNKNOWN`) do `trade_mode` da conta.

    - `None` ou valor fora da faixa -> `UNKNOWN` (ausencia medida, nao zero).
    - `str` -> normalizada em caixa alta, porque alguns dublos de teste e
      alguns campos JSON trazem o rotulo direto.
    """
    if trade_mode is None or isinstance(trade_mode, bool):
        return "UNKNOWN"
    if isinstance(trade_mode, str):
        texto = trade_mode.strip().upper()
        return texto if texto in ROTUOLO_PARA_MODO else "UNKNOWN"
    try:
        valor = int(trade_mode)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return modo_numero_para_rotulo().get(valor, "UNKNOWN")


def conta_e_demo(trade_mode: Any) -> bool:
    """Verdadeiro somente para conta DEMO.

    `CONTEST` NAO e demo: contestacao opera dinheiro de verdade emaze
    premiacoes. Por isso o predicado e exacto, e nao "nao e real".
    """
    return modo_da_conta(trade_mode) == "DEMO"
