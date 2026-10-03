# -*- coding: utf-8 -*-
"""Anexar Expert Advisors a graficos do terminal MT5.

O QUE ISTO FAZ
==============
Grava o bloco `<expert>` no arquivo de perfil do grafico (`.chr`), que e como o
MetaTrader persiste "qual EA esta neste grafico, com quais entradas". Depois de
gravar, o EA aparece anexado ao abrir o perfil no terminal.

FORMATO (verificado nos graficos deste terminal)
===============================================
`MQL5/Profiles/Charts/<perfil>/chartNN.chr` e XML em UTF-16, comecando em
`?<chart>`. O bloco de EA e:

    <expert>
    name=XAU_AI_PRO
    path=Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5
    expertmode=5
    <inputs>
    AutoTrade=true
    MagicNumber=2026001
    ...
    </inputs>
    </expert>

`expertmode` observed nos graficos reais: 4 = AutoTrade ligado, 5 = com
ExpertEnable desligado. Trocar por 4 e o que efetivamente liga a execucao
automatica no terminal.

POR QUE ISSO E COMPATIVEL COM A REGRA DO PROJETO
================================================
O projeto mantem intocaveis `.mq4`, `.mq5`, `.mqh`, `.set` e o diretorio
`MQL5/Experts`. Este modulo:

  - NUNCA escreve em `MQL5/Experts` — so LE, para conferir que o .ex5 existe;
  - NUNCA cria, edita ou apaga `.mq5`, `.mqh`, `.mq4` ou `.set`;
  - escreve APENAS `MQL5/Profiles/Charts/<perfil>/chartNN.chr`, que e o
    arquivo de perfil de grafico do TERMINAL do usuario, nao do repositorio.

O codigo-fonte do EA continua sendo do MT5. Esta e a unica forma de dizer ao
terminal "rode este EA aqui", ja que o MT5 nao expoe API para isso.

PRECAUCAO QUE IMPORTA
=====================
O MT5 tem o terminal ABERTO. Ele mantem os perfis em memoria e reescreve os
`.chr` ao sair. Por isso escrever no arquivo com o terminal aberto e perder a
alteracao: o terminal sobrescreve. Este modulo:

  - avisa quando o terminal esta aberto e o trabalho seria descartado;
  - grava um backup do `.chr` antes de qualquer escrita;
  - faz a escrita de forma ATOMICA (arquivo temporario + replace), para nunca
    deixar um perfil corrompido pela metade;
  - exige `XAU_ALLOW_CHART_WRITE=1` para escrever. Sem a variavel, o modulo
    so le e explica o que falta.
"""
from __future__ import annotations

import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Chave para permitir escrita. Sem ela, tudo aqui e somente leitura.
VARIAVEL_PERMITE_ESCRITA = "XAU_ALLOW_CHART_WRITE"

# expertmode: 4 = AutoTrade ligado, 5 = ExpertEnable desligado.
EXPERTMODE_AUTOTRADE = 4
EXPERTMODE_MANUAL = 5

_CAMPO = re.compile(r"^[A-Za-z0-9_]+$")


def _terminal_root() -> Path | None:
    """Raiz do terminal MT5 ativo (a pasta que contem `MQL5`)."""
    explicito = os.getenv("XAU_MT5_TERMINAL_DATA")
    if explicito:
        p = Path(explicito).expanduser()
        if (p / "MQL5").is_dir():
            return p
    try:
        from backend.ea_manager import _terminal_data_dir  # type: ignore

        return _terminal_data_dir()
    except Exception:
        return None


def _charts_dir() -> Path | None:
    root = _terminal_root()
    if root is None:
        return None
    charts = root / "MQL5" / "Profiles" / "Charts"
    return charts if charts.is_dir() else None


def terminal_aberto() -> bool:
    """O terminal esta em execucao?

    Se estiver, gravar perfil e trabalho perdido: o MT5 reescreve os .chr ao
    sair. Verificamos por ANY / *.lock na pasta de dados do terminal, que o
    MT5 cria e remove sozinho.
    """
    root = _terminal_root()
    if root is None:
        return False
    try:
        for _ in root.glob("*/lock*"):
            return True
    except OSError:
        pass
    return False


def listar_graficos() -> dict[str, Any]:
    """Graficos dos perfis, com simbolo e EA ja anexado."""
    charts = _charts_dir()
    if charts is None:
        return {
            "ok": False,
            "error": "pasta de graficos nao localizada",
            "graficos": [],
            "terminal_aberto": terminal_aberto(),
        }
    graficos: list[dict[str, Any]] = []
    try:
        perfis = sorted(p for p in charts.iterdir() if p.is_dir())
    except OSError as exc:
        return {"ok": False, "error": str(exc), "graficos": [], "terminal_aberto": terminal_aberto()}
    for perfil in perfis:
        try:
            arquivos = sorted(perfil.glob("*.chr"))
        except OSError:
            continue
        for arquivo in arquivos:
            info = ler_grafico(arquivo)
            if info.get("ok"):
                info["perfil"] = perfil.name
                graficos.append(info)
    return {
        "ok": True,
        "charts_dir": str(charts),
        "graficos": graficos,
        "count": len(graficos),
        "terminal_aberto": terminal_aberto(),
        "escrita_permitida": os.getenv(VARIAVEL_PERMITE_ESCRITA) == "1",
    }


def _parse_linhas_chave_valor(bloco: str) -> dict[str, str]:
    """Parseia `chave=valor` por linha.

    O XML do MT5 e apenas "XML de contorno": dentro de <expert> e <inputs> o
    conteudo sao LINHAS de texto `chave=valor`, nao elementos XML. Por isso
    `findtext("name")` e `for filho in <inputs>` devolvem vazio/nada — o
    ElementTree trata tudo como text node. A unica forma de ler e parsear as
    linhas.
    Detalhe que custou um bug: quando o <expert> e o PRIMEIRO filho de <chart>,
    o ElementTree nao poe o texto anterior em 
aiz.text - poe em
    expert.tail. Por isso o leitor de <chart> soma 	ext com o 	ail do
    primeiro filho; sem isso, symbol e period_size desaparecem do resultado.
    """
    saida: dict[str, str] = {}
    for linha in (bloco or "").splitlines():
        limpa = linha.strip()
        if not limpa or "=" not in limpa:
            continue
        chave, _, valor = limpa.partition("=")
        chave = chave.strip()
        if chave:
            saida[chave] = valor.strip()
    return saida


def _texto_com_tail(elemento: ET.Element) -> str:
    """Texto do elemento somado ao 	ail do primeiro filho.

    Se o elemento tem filhos, o texto que vem DEPOIS da tag de abertura e antes
    do primeiro filho mora em .text; o que vem depois do primeiro filho mora
    em .tail do proprio filho. Os dois podem conter as linhas chave=valor
    que nos interessam.
    """
    partes = [elemento.text or ""]
    filhos = list(elemento)
    if filhos:
        partes.append(filhos[0].tail or "")
    return "".join(partes)


def ler_grafico(arquivo: Path) -> dict[str, Any]:
    """Le um .chr e devolve simbolo, timeframe e o EA anexado (se houver)."""
    try:
        bruto = arquivo.read_bytes()
    except OSError as exc:
        return {"ok": False, "error": str(exc), "arquivo": str(arquivo)}
    try:
        texto = bruto.decode("utf-16")
    except UnicodeDecodeError:
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            return {"ok": False, "error": "codificacao do grafico nao reconhecida", "arquivo": str(arquivo)}
    # O arquivo abre com `?<chart>` (XML invertido, para o terminal tolerar
    # gravacao parcial). Removemos o `?` inicial e devolvemos uma declaracao
    # XML normal. A versao anterior usava lstrip("?"), que tambem removia
    # interrogacoes de outros lugares do conteudo.
    limpo = texto.lstrip()
    if limpo.startswith("?"):
        limpo = "<?xml version=\"1.0\"?>" + limpo[1:]
    try:
        raiz = ET.fromstring(limpo)
    except ET.ParseError as exc:
        return {"ok": False, "error": f"XML invalido: {exc}", "arquivo": str(arquivo)}

    # Todos os campos deste formato sao linhas `chave=valor` do text node —
    # inclusive os de <chart> (symbol, period_size, ...). findtext() nao
    # funciona em nenhum deles; o parser de linhas e o caminho unico.
    campos = _parse_linhas_chave_valor(_texto_com_tail(raiz))

    expert = raiz.find("expert")
    entradas: dict[str, str] = {}
    anexado = None
    if expert is not None:
        anexado_linhas = _parse_linhas_chave_valor(_texto_com_tail(expert))
        anexado = {
            "name": anexado_linhas.get("name", ""),
            "path": anexado_linhas.get("path", ""),
            "expertmode": anexado_linhas.get("expertmode", ""),
        }
        bloco = expert.find("inputs")
        if bloco is not None:
            entradas = _parse_linhas_chave_valor(_texto_com_tail(bloco))
    return {
        "ok": True,
        "arquivo": str(arquivo),
        "id": campos.get("id", ""),
        "symbol": campos.get("symbol", ""),
        "description": campos.get("description", ""),
        "period_size": campos.get("period_size", ""),
        "period_type": campos.get("period_type", ""),
        "expert": anexado,
        "inputs": entradas,
    }


def _montar_bloco_expert(nome: str, caminho_rel: str, entradas: dict[str, str], autotrade: bool) -> str:
    modo = EXPERTMODE_AUTOTRADE if autotrade else EXPERTMODE_MANUAL
    linhas = [
        "<expert>",
        f"name={nome}",
        f"path={caminho_rel}",
        f"expertmode={modo}",
        "<inputs>",
    ]
    for chave in sorted(entradas):
        if not _CAMPO.match(chave):
            # Chave fora do padrao quebraria o XML do terminal.
            continue
        valor = str(entradas[chave]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        linhas.append(f"{chave}={valor}")
    linhas += ["</inputs>", "</expert>"]
    return "\n".join(linhas)


def anexar_ea(
    arquivo_grafico: Path,
    nome_ea: str,
    caminho_rel: str,
    entradas: dict[str, str] | None = None,
    autotrade: bool = True,
) -> dict[str, Any]:
    """Escreve o bloco `<expert>` no grafico, com backup e escrita atomica.

    `caminho_rel` e relativo a `MQL5/`, como o terminal grava
    (ex.: `Experts\\XAU_AI_PRO\\XAU_AI_PRO.ex5`).
    """
    if os.getenv(VARIAVEL_PERMITE_ESCRITA) != "1":
        return {
            "ok": False,
            "error": (
                f"escrita de grafico desabilitada. Defina {VARIAVEL_PERMITE_ESCRITA}=1 "
                "para permitir que o app anexe EAs a graficos."
            ),
            "read_only": True,
        }
    if not arquivo_grafico.exists():
        return {"ok": False, "error": f"grafico inexistente: {arquivo_grafico}"}

    atual = ler_grafico(arquivo_grafico)
    if not atual.get("ok"):
        return {"ok": False, "error": atual.get("error", "falha ao ler o grafico")}

    root = _terminal_root()
    if root is not None:
        alvo = root / "MQL5" / caminho_rel.replace("\\", "/")
        if not alvo.exists():
            return {
                "ok": False,
                "error": f"EA nao encontrado no terminal: {alvo}",
                "caminho": str(alvo),
            }

    if terminal_aberto():
        return {
            "ok": False,
            "error": (
                "terminal MT5 aberto: ele mantem os perfis em memoria e reescreve "
                "os .chr ao sair, descartando a alteracao. Feche o MT5 e tente de novo."
            ),
            "terminal_aberto": True,
        }

    texto_bruto = arquivo_grafico.read_bytes()
    try:
        texto = texto_bruto.decode("utf-16")
    except UnicodeDecodeError:
        texto = texto_bruto.decode("utf-8", errors="replace")
    if "encoding" not in texto[:80].lower() and texto.startswith("?<?xml"):
        texto = texto[1:]

    # Remove o <expert> anterior. O padrao e NAO-guloso de forma proposital:
    # precisa casar ate o ultimo </expert> antes de <window> ou </chart>,
    # senao um bloco <inputs> aninhado deixaria o resto do grafico (symbol,
    # period_size) dentro de <inputs> e o terminal leria o perfil errado.
    limpo = re.sub(r"[ \t]*<expert>.*?</expert>\r?\n", "", texto, flags=re.DOTALL)
    bloco = _montar_bloco_expert(nome_ea, caminho_rel, entradas or {}, autotrade)

    # O <expert> entra logo apos a tag de abertura <chart>, que e onde o
    # terminal o lida. Procurar `</chart>` e errado: <chart> e a tag RAIZ
    # deste formato e o `</chart>` final fecha o documento inteiro.
    m = re.search(r"<chart\s*>", limpo)
    if not m:
        return {"ok": False, "error": "estrutura do grafico inesperada (sem <chart>)"}
    # Separa com CRLF: e o terminador de linha que o terminal usa, e as linhas
    # `chave=valor` so sao lidas se estiverem em linhas proprias.
    novo = limpo[: m.end()] + "\r\n" + bloco.replace("\n", "\r\n") + "\r\n" + limpo[m.end():].lstrip("\r\n")

    # Backup antes de escrever: perfil corrompido e pior do que EA nao anexado.
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup = arquivo_grafico.with_suffix(f".chr.bak-{carimbo}")
    try:
        shutil.copy2(arquivo_grafico, backup)
    except OSError as exc:
        return {"ok": False, "error": f"nao foi possivel criar backup: {exc}"}

    # Escrita atomica: temporario + replace. O terminal nunca ve meio arquivo.
    temporario = arquivo_grafico.with_suffix(".chr.tmp")
    try:
        codificacao = "utf-16" if texto_bruto[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        temporario.write_bytes(novo.encode(codificacao))
        os.replace(temporario, arquivo_grafico)
    except OSError as exc:
        temporario.unlink(missing_ok=True)
        return {"ok": False, "error": f"falha ao gravar o grafico: {exc}", "backup": str(backup)}

    return {
        "ok": True,
        "arquivo": str(arquivo_grafico),
        "backup": str(backup),
        "expert": nome_ea,
        "path": caminho_rel,
        "expertmode": EXPERTMODE_AUTOTRADE if autotrade else EXPERTMODE_MANUAL,
        "autotrade": autotrade,
        "inputs": len(entradas or {}),
        "anexado_em": datetime.now(timezone.utc).isoformat(),
    }


def anexar_ea_por_nome(
    perfil: str,
    nome_grafico: str,
    nome_ea: str,
    caminho_rel: str,
    entradas: dict[str, str] | None = None,
    autotrade: bool = True,
) -> dict[str, Any]:
    """Atalho por nome: resolve perfil/grafico e chama `anexar_ea`."""
    charts = _charts_dir()
    if charts is None:
        return {"ok": False, "error": "pasta de graficos nao localizada"}
    arquivo = charts / perfil / nome_grafico
    if not arquivo.exists():
        disponiveis = sorted(p.name for p in (charts / perfil).glob("*.chr")) if (charts / perfil).is_dir() else []
        return {
            "ok": False,
            "error": f"grafico {nome_grafico} nao existe em {perfil}",
            "disponiveis": disponiveis,
        }
    return anexar_ea(arquivo, nome_ea, caminho_rel, entradas, autotrade)
