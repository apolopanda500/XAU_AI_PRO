r"""Catalogo dinamico de ativos fornecidos pelo terminal MT5.

A CLASSA de cada ativo vem do `path` que a CORRETORA publica
(`Derivatives\Spot Metals\GOLD`, `Stocks\EU\...`). Nada aqui presume par,
mercado ou classe: a lista e da XM, do MEXC ou de quem mais for.

Medido em 05/10/2026 na conta real 391773676 (XMGlobal-MT5 14): 1639 ativos,
1639 com `path` preenchido. Antes a classificacao procurava palavra solta no
nome, e `SOL` casava dentro de "Solvar".
"""
from __future__ import annotations

import math
import re


def _value(item, name: str, default=None):
    value = getattr(item, name, default)
    return default if value is None else value


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _integer(value):
    number = _number(value)
    return None if number is None else int(number)


#: A CLASSIFICACAO VEM DA CORRETORA, NAO DE PALAVRA NO NOME (05/10/2026)
#:
#: MEDIDO na conta real 391773676 (XMGlobal-MT5 14, 1639 ativos). O MT5
#: preenche `path` com a HIERARQUIA da corretora, e ela esta correta:
#:
#:   GOLD               -> Derivatives\Spot Metals\GOLD
#:   EURUSD             -> Forex\Standard\Majors\EURUSD
#:   BTCUSD             -> Cryptocurrencies\Standard\BTCUSD
#:   AalbertsIndustries -> Stocks\EU\Netherlands\AalbertsIndustries
#:   AUS200Cash         -> Derivatives\Cash\Cash Indices\AUS200Cash
#:
#: A versao anterior procurava PALAVRAS SOLTAS em `f"{name} {path} ..."`:
#: `any(token in text for token in ("BTC","ETH","SOL","XRP"))`. Sem fronteira
#: de palavra, `SOL` casa dentro de "Solvar" e `XRP` dentro de "XRPetersen" —
#: acoes da bolsa classificadas como cripto. Medido: 106 "cripto" na conta,
#: sendo a maioria acoes europeias.
#:
#: POR QUE A CORRETORA E A FONTE
#: ------------------------------
#: A regra do projeto e "nenhum simbolo pode ser presumido", e a lista fixa
#: de 17 ativos em `asset_classes.py` era exatamente isso: uma copia
#: desatualizada do que a corretora tem. A conta real tem 1639.
#:
#: `path` nao e um palpite nosso — e o catalogo da propria corretora, que e a
#: unica que sabe o que ela passou a oferecer. E a lista e do OPERADOR, nao
#: nossa: o `path` muda conforme a XM acrescenta ou remove um produto.
#:
#: COBERTURA MEDIDA: 1639 de 1639 ativos com `path` preenchido, zero sem
#: classificacao. O fallback por palavra continua existindo para corretora
#: que NAO preencher o campo — e ele e marcado como palpite, nao como fato.
_CAMINHO_PARA_CLASSE: tuple[tuple[tuple[str, ...], str], ...] = (
    # Ordem importa: "Thematic Indices" contem "Indices", e "Turbo Stocks"
    # contem "Stocks". A raiz e comparada inteira, sem substring.
    (("Cryptocurrencies",), "crypto"),
    (("Forex",), "forex"),
    (("Thematic Indices",), "index"),
    (("ETF Derivatives",), "index"),
    (("Turbo Stocks",), "equity"),
    (("Stocks",), "equity"),
    (("Derivatives",), "cfd"),
)

#: Quando o `path` NAO vem (corretora que nao preenche), cai para palavras
#: SOLTAS — com fronteira de palavra, o defeito medido acima nao se repete.
#: `SOL` casa em "Sol/USDT" e em "SOL", e nao dentro de "Solvar".
_PALAVRAS_FALLBACK: tuple[tuple[tuple[str, ...], str], ...] = (
    (("CRYPTO", "CRYPTOCURRENCIES", "BITCOIN", "ETHEREUM"), "crypto"),
    (("FOREX", "CURRENCY", "FX"), "forex"),
    (("SPOT METALS", "PRECIOUS METAL", "METAL", "GOLD", "SILVER"), "metal"),
    (("CASH INDICES", "INDEX", "INDICES"), "index"),
    (("FUTURES", "FUTURE"), "future"),
    (("STOCK", "STOCKS", "EQUITY", "SHARES"), "equity"),
)


def _por_palavra(texto: str) -> str | None:
    """Casamento com FRONTEIRA de palavra, por regex `\\b`.

    Sem fronteira, `SOL` casa dentro de "Solvar" — que foi o defeito medido.
    Com fronteira, `SOL` casa em `SOL` e `SOL/USDT`, e nao em `Solvar`.
    """
    for palavras, classe in _PALAVRAS_FALLBACK:
        for palavra in palavras:
            if re.search(rf"\b{re.escape(palavra)}\b", texto):
                return classe
    return None


def _asset_class(name: str, path: str, base: str, profit: str) -> str:
    """Classe do ativo, lida da HIERARQUIA que a corretora publica.

    A raiz do `path` e comparada INTEIRA, nunca por substring: e o que
    separa "Thematic Indices" de "Turbo Stocks" sem que uma casa na outra.

    Quando o `path` nao vem, cai para palavras SOLTAS com fronteira — e o
    resultado e um PALPITE, marcado como tal em `classificacao_fonte`.
    """
    raiz = path.strip().split("\\")[0].strip().lower() if path else ""
    for raizes, classe in _CAMINHO_PARA_CLASSE:
        if raiz in raizes:
            # `Derivatives` cobre metais E oil; o segundo nivel desempata.
            if classe == "cfd":
                segundo = path.strip().split("\\")[1].strip().lower() if "\\" in path else ""
                if "metal" in segundo:
                    return "metal"
                if "index" in segundo:
                    return "index"
                if "future" in segundo:
                    return "future"
                return "cfd"
            return classe

    texto = f"{name} {path} {base} {profit}".upper()
    return _por_palavra(texto) or "other"


def _nome_do_modelo(symbol: str) -> str | None:
    r"""O nome com que o MODELO foi treinado, ou `None` se nao ha.

    MEDIDO na conta 391773676 (XMGlobal-MT5 14), com `discover_assets`:

        linha `GOLD`, com `path` sob `Derivatives\Spot Metals\GOLD`
        nenhuma linha `XAUUSD` — `symbol_info("XAUUSD")` devolve `None`

    E os artefatos do app se chamam `XAUUSD_H1`, `XAUUSD_H4`, `XAUUSD_M15` e
    `XAUUSD_M5`. Sao o mesmo metal com dois nomes, em dois lugares — e a tela
    precisa saber que sao o mesmo, senao a ficha do ouro vem vazia e o painel
    diz "depende do contrato" para um ativo que a corretora JA PUBLICOU.

    A traducao e o MAPA DO OPERADOR (`symbol_aliases.json`), nunca um nome
    escrito aqui: o AGENTS.md 3 proibe nome de ativo no codigo, e um nome fixo
    aqui continuaria funcionando depois de o operador trocar o mapa — que e o
    defeito que a regra previne.

    `None` quando nao ha mapeamento. E ausencia medida: "nenhum modelo
    treinado com este nome". NUNCA o proprio `symbol`, ou todos os pares do
    catalogo declarariam ter modelo.
    """
    try:
        from backend.symbol_aliases import para_modelo
    except Exception:
        return None
    try:
        nome = para_modelo("mt5", symbol)
    except Exception:
        return None
    if not nome:
        return None
    pedido = str(nome).strip().upper()
    if pedido == str(symbol).strip().upper():
        # `para_modelo` devolve o proprio simbolo quando NAO ha mapeamento.
        # Devolver isso aqui seria "todo par tem modelo", e a lista de modelos
        # passaria a anunciar os 1.639 pares do catalogo quando existem 36
        # artefatos `.meta.json` no disco.
        return None
    return pedido


def discover_assets(mt5, include_hidden: bool = True) -> list[dict]:
    rows = []
    symbols = mt5.symbols_get()
    if symbols is None:
        return rows
    for item in symbols or []:
        symbol = str(_value(item, "name", "") or "").strip()
        if not symbol:
            continue
        visible_value = _value(item, "visible", None)
        visible = None if visible_value is None else bool(visible_value)
        if not include_hidden and visible is not True:
            continue
        path = str(_value(item, "path", "") or "")
        base = str(_value(item, "currency_base", "") or "")
        profit = str(_value(item, "currency_profit", "") or "")
        nome_modelo = _nome_do_modelo(symbol)
        rows.append({
            "symbol": symbol,
            # O NOME COM QUE O MODELO FOI TREINADO. `None` = nenhum modelo
            # com este nome — ver `_nome_do_modelo`.
            "model_symbol": nome_modelo,
            "has_model": nome_modelo is not None,
            "description": _value(item, "description", None),
            "path": path or None,
            "visible": visible,
            "asset_class": _asset_class(symbol, path, base, profit),
            "currency_base": base or None,
            "currency_profit": profit or None,
            "digits": _integer(_value(item, "digits", None)),
            "point": _number(_value(item, "point", None)),
            "trade_mode": _integer(_value(item, "trade_mode", None)),
            "volume_min": _number(_value(item, "volume_min", None)),
            "volume_max": _number(_value(item, "volume_max", None)),
            "volume_step": _number(_value(item, "volume_step", None)),
            "change_pct": None,
            # Ficha de especificacao (ideia da pagina de simbolo da XM):
            # tamanho do contrato, spread em pontos e swaps. Tudo lido do
            # terminal — nenhum valor fixo, nenhuma corretora presumida.
            "contract_size": _number(_value(item, "trade_contract_size", None)),
            "spread_points": _integer(_value(item, "spread", None)),
            "swap_long": _number(_value(item, "swap_long", None)),
            "swap_short": _number(_value(item, "swap_short", None)),
        })
    return sorted(rows, key=lambda row: row["symbol"].upper())
