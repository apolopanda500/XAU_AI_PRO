# -*- coding: utf-8 -*-
"""Levar o `.ex5` compilado do repositorio para o terminal que roda o EA.

O BURACO QUE ESTE MODULO FECHA
==============================
MEDIDO em 11/10/2026, no terminal D0E8209F...:

    repo     MQL5/Experts/XAU_AI_PRO/XAU_AI_PRO.ex5   10/10 21:00  (fresco)
    terminal MQL5/Experts/XAU_AI_PRO/XAU_AI_PRO.ex5   08/10 23:03  (2 dias velho)

O `tests/test_mql5_compila.py` compila o `.mq5` do REPO com o MetaEditor e o
`.ex5` nasce AO LADO, no repo. Mas o grafico so carrega EA de `MQL5/Experts` do
TERMINAL, que e outra pasta (o repo vive sob `MQL5/Files/XAU_AI_PRO`, sandbox de
dados que nao carrega EA). Resultado: **compilar nao atualiza o que opera**.
Reanexar o EA ao grafico recarrega o `.ex5` que JA estava no terminal — o velho.
Foi assim que, em 11/10, um EA defasado ficou operando a conta real 391773676
(1132 tentativas de venda de EURUSD no journal de domingo).

`backend/ea_manager.py` INVENTARIA (le o terminal) e `backend/chart_attach.py`
ANEXA (escreve o `.chr`). Nenhum dos dois copia o binario compilado. Este modulo
faz exatamente essa copia, e so ela.

POR QUE SO O `.ex5`, E NAO OS FONTES
====================================
O `Temp/portar_spread_terminal.py` mediu, em 08/10/2026, que as duas arvores tem
20 arquivos diferentes — e a divergencia vai nos DOIS sentidos: o repo esta mais
novo em 16 (Config, CircuitBreaker, ExecutionEngine, ...) e o TERMINAL em 4
(HealthMonitor com um bloco "TESTER-AWARE" de 107 linhas, DecisionEngine,
SignalCore, Dashboard). Sincronizar fontes repo->terminal DESTRUIRIA essas 107
linhas e reverteria a API do sinal. Por isso aqui se copia SO o `.ex5`, que e
autocontido (ja compilado) e nao depende dos `.mqh` em disco.

O QUE ESTE MODULO NAO FAZ
=========================
- NUNCA escreve no `MQL5/Experts` do REPO. So le o `.ex5` de la (a origem).
- NUNCA copia `.mq5`/`.mqh`/`.mq4`/`.set`. So o `.ex5`.
- NUNCA reanexa o grafico. Copiar o binario so tem efeito quando o operador
  reanexa/atualiza o EA no MT5 — o EA em execucao roda a versao em memoria.
  Este modulo AVISA disso; nao finge que copiar basta.
- NUNCA envia ordem. Execucao continua sendo do EA no terminal.

SEGURANCA
=========
Somente leitura por padrao. Copiar exige `XAU_ALLOW_EA_DEPLOY=1` (o mesmo
desenho do `chart_attach`, que exige `XAU_ALLOW_CHART_WRITE=1`). Sem a variavel,
o modulo so MEDE e diz o que esta defasado. Com ela, grava backup do destino
antes de sobrescrever e copia de forma atomica.

A comparacao e por HASH, nunca por data: a data do arquivo pode bater com o
conteudo diferente (e o contrario). E a licao do AGENTS.md §7.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

#: Copia exige esta variavel. Sem ela, dry-run: o modulo so mede.
VARIAVEL_PERMITE_DEPLOY = "XAU_ALLOW_EA_DEPLOY"

#: Raiz do projeto (este arquivo esta em backend/).
RAIZ = Path(__file__).resolve().parent.parent

#: O binario compilado que o teste de compilacao gera, ao lado do fonte.
REPO_EX5 = RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.ex5"

#: Bytes lidos para o hash. Um .ex5 tem ~430 KB; 8 MB cobre qualquer EA.
LIMITE_HASH = 8 * 1024 * 1024


def _repo_ex5() -> Path:
    """Caminho do `.ex5` no REPO (a origem da verdade do build)."""
    return REPO_EX5


def _terminal_ex5() -> Path | None:
    """Caminho do `.ex5` no TERMINAL (o que o grafico carrega).

    Varre `%APPDATA%\\MetaQuotes\\Terminal` por uma subpasta que tenha
    `MQL5\\Experts`, que e o irmao de `MQL5\\Files`. Mesma logica de
    `mt5_bridge.get_mt5_data_path()`, mas sem depender de `mt5_bridge` estar no
    `sys.path`: MEDIDO que, sem `Python/` no path, `chart_attach._terminal_root()`
    devolvia `None` (o `from mt5_bridge import` falhava em silencio) — e o
    modulo quebrava. Aqui a varredura e propria, e `XAU_MT5_TERMINAL_DATA` tem
    prioridade para quem quiser apontar o terminal explicitamente.
    """
    explicito = os.getenv("XAU_MT5_TERMINAL_DATA")
    if explicito:
        p = Path(explicito).expanduser()
        if (p / "MQL5" / "Experts").is_dir():
            return p / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.ex5"

    appdata = os.getenv("APPDATA")
    if appdata:
        terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
        if terminal_root.is_dir():
            for sub in sorted(terminal_root.iterdir()):
                if (sub / "MQL5" / "Experts").is_dir():
                    return sub / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.ex5"
    return None



def _sha256(caminho: Path) -> str:
    """SHA-256 do arquivo, limitado a `LIMITE_HASH` bytes. Vazio se nao ler."""
    try:
        h = hashlib.sha256()
        with caminho.open("rb") as fh:
            restante = LIMITE_HASH
            while restante > 0:
                bloco = fh.read(min(65536, restante))
                if not bloco:
                    break
                h.update(bloco)
                restante -= len(bloco)
        return h.hexdigest()
    except OSError:
        return ""


def _info(caminho: Path | None) -> dict[str, Any]:
    """Resumo de um `.ex5`: existe, hash, tamanho, data. Sem inventar."""
    if caminho is None or not caminho.is_file():
        return {
            "existe": False,
            "hash": "",
            "bytes": 0,
            "modificado_em": None,
            "caminho": str(caminho) if caminho else None,
        }
    st = caminho.stat()
    return {
        "existe": True,
        "hash": _sha256(caminho),
        "bytes": st.st_size,
        "modificado_em": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "caminho": str(caminho),
    }


def estado_deploy(origem: Path | None = None, destino: Path | None = None) -> dict[str, Any]:
    """Compara o `.ex5` do repo com o do terminal, SO LEITURA.

    `defasado` e decidido por HASH, nao por data. Se o destino nao existe, esta
    defasado (o terminal nao tem o binario). Se os hashes batem, atualizado.
    """
    origem = _repo_ex5() if origem is None else origem
    destino = _terminal_ex5() if destino is None else destino

    o = _info(origem)
    d = _info(destino)

    if not o["existe"]:
        # Sem o .ex5 do repo nao ha o que deployar: o teste de compilacao e que
        # o gera. Aqui nao compilamos — reportamos a falta com motivo.
        situacao = "sem_binario_no_repo"
        defasado = False
    elif not d["existe"]:
        situacao = "terminal_sem_binario"
        defasado = True
    elif o["hash"] == d["hash"]:
        situacao = "atualizado"
        defasado = False
    else:
        situacao = "defasado"
        defasado = True

    return {
        "ok": o["existe"],
        "origem": o,
        "destino": d,
        "defasado": defasado,
        "situacao": situacao,
        "aviso": (
            "Copiar o .ex5 tem efeito so ao REANEXAR o EA no grafico: o EA em "
            "execucao roda a versao em memoria. Reanexar nao copia o binario."
        ),
        "nota": (
            "A comparacao e por hash. Data igual com conteudo diferente (ou o "
            "contrario) e possivel, e por isso a data nao decide aqui."
        ),
    }


def sincronizar_ex5(
    origem: Path | None = None,
    destino: Path | None = None,
    backup_dir: Path | None = None,
    aplicar: bool = True,
) -> dict[str, Any]:
    """Copia o `.ex5` do repo para o terminal, com backup e de forma atomica.

    So copia se:
      * `aplicar=True` (dry-run por omissao e `aplicar=False`);
      * a variavel `XAU_ALLOW_EA_DEPLOY` estiver `1`;
      * existir o `.ex5` de origem no repo;
      * os hashes diferirem (idempotente: atualizado nao copia de novo).

    Se o destino existia, grava backup antes de sobrescrever. Escreve em arquivo
    temporario e faz `os.replace` (atomico), para nunca deixar um binario pela
    metade. NUNCA escreve no repo.
    """
    est = estado_deploy(origem, destino)
    if not est["ok"]:
        return {**est, "acao": "sem_origem"}

    caminho_destino = est["destino"]["caminho"]
    if caminho_destino is None:
        # Terminal nao resolvido: nao ha para onde copiar. Reportar com motivo e
        # o oposto de quebrar com TypeError em Path(None) — MEDIDO que esse era
        # o comportamento antes desta guarda.
        return {
            **est,
            "acao": "sem_terminal",
            "destino_final": None,
            "como_resolver": (
                "aponte o terminal com XAU_MT5_TERMINAL_DATA=<raiz com MQL5/Experts> "
                "ou garanta %APPDATA%\\MetaQuotes\\Terminal com uma subpasta que tenha MQL5\\Experts"
            ),
        }

    alvo = Path(caminho_destino)

    if not est["defasado"]:
        return {**est, "acao": "ja_atualizado", "destino_final": str(alvo)}

    if not aplicar:
        return {**est, "acao": "dry_run", "destino_final": str(alvo)}

    if os.getenv(VARIAVEL_PERMITE_DEPLOY) != "1":
        return {
            **est,
            "acao": "sem_autorizacao",
            "destino_final": str(alvo),
            "como_autorizar": f"defina {VARIAVEL_PERMITE_DEPLOY}=1 para copiar de verdade",
        }

    origem_path = Path(est["origem"]["caminho"])

    # Backup do destino ANTES de sobrescrever, se ele existir.
    backup = None
    if alvo.is_file() and backup_dir is not None:
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = backup_dir / f"XAU_AI_PRO.ex5.bak-{carimbo}"
            shutil.copy2(alvo, backup)
        except OSError as exc:
            return {**est, "acao": "falha_backup", "erro": str(exc), "destino_final": str(alvo)}

    alvo.parent.mkdir(parents=True, exist_ok=True)
    temporario = alvo.with_suffix(".ex5.tmp")
    try:
        shutil.copy2(origem_path, temporario)
        os.replace(temporario, alvo)
    except OSError as exc:
        temporario.unlink(missing_ok=True)
        return {
            **est,
            "acao": "falha_copia",
            "erro": str(exc),
            "destino_final": str(alvo),
            "backup": str(backup) if backup else None,
        }

    depois = _info(alvo)
    return {
        **est,
        "acao": "copiado",
        "backup": str(backup) if backup else None,
        "destino_final": str(alvo),
        "hash_apos": depois["hash"],
        "hash_confere": depois["hash"] == est["origem"]["hash"],
        "defasado": False,
        "situacao": "atualizado",
    }
