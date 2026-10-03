# -*- coding: utf-8 -*-
"""Gestao de Expert Advisors no terminal MT5.

O QUE ISTO FAZ E POR QUE
========================
O MT5 NAO EXECUTA EA VIA API PYTHON. Nao existe funcao `mt5.ea_start()`. O
terminal so executa Expert Advisors compilados (`.ex5`) num grafico, com
`ExpertEnable` ligado. Qualquer ferramenta que prometa "rodar EA pelo gateway"
esta descrevendo algo que o MetaTrader nao faz.

O que o app PODE fazer, e e o que este modulo faz:

  1. INVENTARIAR os EAs realmente instalados no terminal do usuario
     (ler `MQL5/Experts` do terminal ativo, incluindo subpastas), com tamanho,
     data e hash do arquivo. Nada inventado: se o arquivo nao existe, o EA
     nao aparece.

  2. DELEGAR a execucao ao MT5. Para um EA rodar, ele precisa estar na pasta
     de experts do terminal e anexado a um grafico. O app preparea o terreno
     (caminho, permissao, existencia) e reporta o que falta — quem anexa ao
     grafico e o usuario, no proprio MT5.

  3. OBSERVAR quem esta rodando. O heartbeat (`backend/watchdog.py`) e o
     journal do terminal dizem se um EA esta vivo. Aqui os cruzamos com o
     inventario para dizer, por EA: instalado, presente no heartbeat, com
     que estado.

O QUE ISTO NAO FAZ
==================
- Nao compila EA, nao inventa `.ex5`, nao escreve em `MQL5/Experts` do
  repositorio. O repositorio mantem os MQL5 intocaveis por decisao do projeto;
  este modulo apenas LE a pasta do TERMINAL do usuario e nunca a do repositorio.
- Nao envia ordem. Execucao continua sendo do EA no MT5, com as travas do
  gateway. Um EA de terceiro aqui aparece como somente leitura.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Extensoes que o MT5 consegue executar num grafico.
EXTENSOES_EXECUTAVEIS = {".ex5"}
# Extensoes de codigo-fonte: uteis para Inventariar, mas NAO executaveis.
EXTENSOES_FONTE = {".mq5", ".mqh", ".mq4", ".mq4h"}
NOME_EA_PESQUISA = re.compile(r"\.ex5$", re.IGNORECASE)


def _terminal_data_dir() -> Path | None:
    """Pasta de dados do terminal MT5 ativo.

    Deriva de `MQL5/Experts` sob `.../MQL5/Files/`, que e onde o MT5 grava.
    A ordem de busca vai do caminho explicito ate a busca do proprio MT5.
    """
    explicito = os.getenv("XAU_MT5_TERMINAL_DATA")
    if explicito:
        p = Path(explicito).expanduser()
        if (p / "MQL5" / "Experts").exists():
            return p
    try:
        from mt5_bridge import get_mt5_data_path  # type: ignore

        dados = Path(get_mt5_data_path()).resolve()
        # Layout real do MT5:
        #   Terminal/<id>/MQL5/Files/Data   <- get_mt5_data_path()
        #   Terminal/<id>/MQL5/Experts      <- os Expert Advisors
        # `MQL5/Experts` e IRMAO de `MQL5/Files`. O valor devolvido e a raiz
        # do terminal, e quem procura `MQL5/Experts` a partir dele.
        for base in dados.parents:
            if base.name == "Terminal":
                for sub in sorted(base.iterdir()):
                    if (sub / "MQL5" / "Experts").is_dir():
                        return sub
    except Exception:
        pass
    return None


def _hash_arquivo(caminho: Path, limite: int = 8 * 1024 * 1024) -> str:
    """SHA-256 do arquivo, ou string vazia se nao der para ler.

    Nao lemos o arquivo inteiro se ele for gigante: um .ex5 de 200 MB nao deve
    travar a tela do inventario.
    """
    try:
        h = hashlib.sha256()
        with caminho.open("rb") as f:
            lido = 0
            while lido < limite:
                bloco = f.read(1024 * 1024)
                if not bloco:
                    break
                h.update(bloco)
                lido += len(bloco)
        return h.hexdigest()[:16]
    except OSError:
        return ""


def listar_eas_instalados() -> dict[str, Any]:
    """Inventario real dos EAs presentes no terminal. Somente leitura."""
    data_dir = _terminal_data_dir()
    if data_dir is None:
        return {
            "ok": False,
            "status": "terminal_nao_localizado",
            "error": "nao foi possivel localizar a pasta de dados do MT5",
            "read_only": True,
            "experts_dir": None,
            "experts": [],
            "count": 0,
        }
    experts = data_dir / "MQL5" / "Experts"
    if not experts.exists():
        return {
            "ok": False,
            "status": "pasta_inexistente",
            "error": f"pasta de experts ausente: {experts}",
            "read_only": True,
            "experts_dir": str(experts),
            "experts": [],
            "count": 0,
        }

    encontrados: list[dict[str, Any]] = []
    try:
        for caminho in sorted(experts.rglob("*")):
            if not caminho.is_file():
                continue
            sufixo = caminho.suffix.lower()
            if sufixo not in EXTENSOES_EXECUTAVEIS | EXTENSOES_FONTE:
                continue
            try:
                stat = caminho.stat()
            except OSError:
                continue
            try:
                rel = str(caminho.relative_to(experts)).replace("\\", "/")
            except ValueError:
                rel = caminho.name
            encontrados.append({
                "nome": caminho.stem,
                "arquivo": rel,
                "caminho": str(caminho),
                "extensao": sufixo,
                # Somente .ex5 executa num grafico.Fonte (.mq5) precisa de
                # compilacao no MetaEditor, que o app nao faz.
                "executavel": sufixo in EXTENSOES_EXECUTAVEIS,
                "tem_codigo_fonte": caminho.with_suffix(".mq5").exists(),
                "bytes": stat.st_size,
                "modificado_em": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "hash_sha256_16": _hash_arquivo(caminho),
            })
    except OSError as exc:
        return {
            "ok": False,
            "status": "leitura_falhou",
            "error": str(exc),
            "read_only": True,
            "experts_dir": str(experts),
            "experts": [],
            "count": 0,
        }

    executaveis = [e for e in encontrados if e["executavel"]]
    return {
        "ok": True,
        "status": "ok",
        "read_only": True,
        "commands_enabled": False,
        "control_supported": False,
        "experts_dir": str(experts),
        "terminal_data_dir": str(data_dir),
        "experts": encontrados,
        "count": len(encontrados),
        "executaveis": len(executaveis),
        "apenas_fonte": len(encontrados) - len(executaveis),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _heartbeat() -> dict[str, Any]:
    """Estado do heartbeat do EA, se houver. Nunca levanta excecao.

    O heartbeat e acessado na aba de sistema e no inventario. Se o modulo do
    watchdog ou o MT5 estiverem indisponiveis, o chamador recebe dicionario
    vazio em vez de uma excecao derrubando a tela inteira.
    """
    try:
        from backend import watchdog  # type: ignore

        estado = watchdog.ea_state()
        return estado if isinstance(estado, dict) else {}
    except Exception:
        return {}


def _ea_no_journal(nome_ea: str, limite: int = 400) -> dict[str, Any]:
    """Procura o EA nas ultimas linhas do journal. Somente leitura.

    O journal e texto livre. Procuramos o nome do arquivo sem extensao, que e
    como o MT5 identifica o EA no log. Devolvemos se encontramos, quantas
    vezes, e a ultima linha — sem interpretar conteudo alem disso.
    """
    try:
        from backend.mt5_gateway import _journal_lines  # type: ignore
    except Exception:
        return {"presente": False, "ocorrencias": 0, "ultima": None}
    try:
        linhas = _journal_lines(limit=limite)
    except Exception:
        return {"presente": False, "ocorrencias": 0, "ultima": None}
    if not isinstance(linhas, list):
        return {"presente": False, "ocorrencias": 0, "ultima": None}
    alvo = nome_ea.lower()
    ocorrencias = 0
    ultima = None
    for linha in linhas:
        texto = linha if isinstance(linha, str) else str(linha)
        if alvo and alvo in texto.lower():
            ocorrencias += 1
            ultima = texto
    return {"presente": ocorrencias > 0, "ocorrencias": ocorrencias, "ultima": ultima}


def status_eas(com_journal: bool = True) -> dict[str, Any]:
    """Estado por EA: instalado no terminal + vivo no heartbeat/journal.

    Cruzia o inventario de disco com o que o terminal esta reportando. Um EA
    instalado e nao visto no heartbeat provavelmente nao esta anexado a nenhum
    grafico — e isso que dizemos, em vez de afirmar que ele "esta parado".
    """
    inventario = listar_eas_instalados()
    if not inventario.get("ok"):
        return {**inventario, "heartbeat": _heartbeat(), "detalhado": []}

    hb = _heartbeat()
    hb_estado = str(hb.get("state", "unknown"))

    detalhado: list[dict[str, Any]] = []
    for item in inventario["experts"]:
        if not item["executavel"]:
            continue
        j = _ea_no_journal(item["nome"]) if com_journal else {
            "presente": False, "ocorrencias": 0, "ultima": None,
        }
        # "vivo" so e afirmado com base em sinal observado. Sem sinal, o
        # estado e desconhecido — nunca "funcionando" por presuncao.
        if hb_estado == "alive" and j["presente"]:
            estado = "vivo"
        elif j["presente"]:
            estado = "visto_no_journal"
        elif hb_estado == "alive":
            estado = "heartbeat_sem_identificar"
        else:
            estado = "sem_sinal"
        detalhado.append({
            **item,
            "estado": estado,
            "no_journal": j["presente"],
            "ocorrencias_journal": j["ocorrencias"],
            "ultima_linha_journal": j["ultima"],
        })

    return {
        **inventario,
        "heartbeat": hb,
        "heartbeat_estado": hb_estado,
        "detalhado": detalhado,
        # Frase honesta: instalados nao e o mesmo que em execucao.
        "nota": (
            "Instalado no terminal nao significa executando: um EA precisa estar "
            "anexado a um grafico no MT5 com ExpertEnable ligado. O app nao "
            "anexa grafico nem compila EA — quem executa e o proprio MT5."
        ),
    }
