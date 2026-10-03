# -*- coding: utf-8 -*-
"""Pre-flight do XAU AI PRO: verifica o ambiente antes de qualquer operacao longa.

Por que existe
--------------
Os erros mais caros deste projeto nao aparecem no codigo: aparecem no meio de
uma operacao. O build do Android consumiu 3,4 GB e so entao o emulador avisou
"not enough space". Um `cmd.exe` de 344 KB na raiz ficou travado porque um
processo do Office o executava. Um script de limpeza aceitava array apenas
quando chamado via `-Command`, e falhava de forma opaca via `-File`.

Todas essas classes de erro sao detectaveis em segundos, antes de gastar
minutos. Este modulo e o ponto unico de verificacao: `python scripts/preflight.py`
imprime o relatorio e sai com codigo 1 se algo bloquear.

O que ele NAO faz
-----------------
Nao altera nada. Somente leitura: disco, ferramentas, portas, permissões,
estado do Git, guarda de MQL5 e presenca dos scripts bloqueados.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ===========================================================
# AUTORIZACOES DE ALTERACAO MQL5 (03/10/2026)
# ===========================================================
# A guarda `checar_mql5()` reprova QUALQUER alteracao em `MQL5/Experts`,
# sem distinguir "esqueci de reverter" de "o dono mandou, eu mexi e documentei".
# Isso ja barrou uma alteracao legitima: o cooldown de margem, medido contra os
# 4.165 `EXEC_NO_MARGIN` do forward test.
#
# A CORRECAO NAO E afrouxar a guarda. E exigir que a autorizacao seja EXPLICITA
# e RASTREVEL: cada entrada deste arquivo declara o arquivo, o commit e o motivo,
# e a guarda so libera o que esta listado aqui.
#
# FORMATO: uma entrada por arquivo autorizado, mais o commit e o motivo.
# A guarda le isto; nao edite a guarda para passar.
#
# REGRA QUE PERMANECE: alterar `.mq5`/`.mqh` exige RECOMPILAR no MetaEditor64
# e REANEXAR ao grafico. A autorizacao para mexer no codigo NAO autoriza a
# reanexao automatica — ela derruba o treino de quem esta operando na DEMO.
# ===========================================================

AUTORIZACOES_MQL5: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------------
    # 03/10/2026 — cooldown de margem (autorizado pelo dono nesta sessao)
    # ---------------------------------------------------------------------
    "Enterprise/MarginChecker.mqh": {
        "commit": "pendente",
        "motivo": (
            "EXEC_NO_MARGIN repetido a cada 2-3 s: 4.165 recusas no forward test, "
            "1.452 num unico dia (17/09). A trava de margem EXISTIA e funcionava; o "
            "defeito era insistir depois de recusado. Cooldown por simbolo com backoff "
            "60 s -> 1 h. Reducao medida de 3.191x nas recusas."
        ),
        "compilado": "sim — MetaEditor64, 0 errors, 0 warnings, XAU_AI_PRO.ex5 419.654 bytes",
        "reanexado": "NAO — attente o treino do dono na conta DEMO",
    },
    "Core/ExecutionEngine.mqh": {
        "commit": "pendente",
        "motivo": (
            "OrderSendResult() NAO existe em MQL5 (error 256), introduzido no commit "
            "dbdce10 e nunca compilado. Nao havia .ex5 versionado para revelar isso. "
            "Substituido por GetLastError() com traducao explicita do ExecResult, para "
            "que o BROKER_ERROR passe a dizer a CAUSA."
        ),
        "compilado": "sim — junto com o acima, 0 errors, 0 warnings",
        "reanexado": "NAO — mesma razao",
    },
}


def _autorizacoes_mql5() -> dict[str, dict[str, str]]:
    """Mapa `arquivo relativo` -> `{commit, motivo, compilado, reanexado}`."""
    return AUTORIZACOES_MQL5


# Espaco minimo livre para as operacoes longas do projeto.
DISCO_MINIMO_GB = 4.0
# Espaco minimo para build Android (Gradle + target Rust).
DISCO_MINIMO_ANDROID_GB = 8.0

# Portas do produto. Todas precisam estar livres antes de subir o app.
PORTAS = {"gateway": 9001, "websocket": 9002, "core": 9003}

# Ferramentas obrigatorias por etapa. No Windows, `npm` e um .cmd e precisa ser
# chamado pelo nome completo; `python` raramente esta no PATH porque o projeto
# usa sempre .venv\Scripts\python.exe (ver checar_python_do_projeto).
FERRAMENTAS = {
    "node": ("node", "--version"),
    "npm": ("npm.cmd" if os.name == "nt" else "npm", "--version"),
    "cargo": ("cargo", "--version"),
}

# Scripts removidos em 2026-09-26. Ver scripts/validate_release.ps1.
SCRIPTS_BLOQUEADOS = (
    "cmd.exe",
    "XAU_AI_PRO_START.vbs",
    "scripts/overnight_session.ps1",
    "scripts/ciclo_limpo_123.py",
    "Tools/pos_reboot_docker.ps1",
    "Tools/post_docker_cli_setup.ps1",
    "Tools/connect_sandbox_claude.ps1",
    "Tools/setup_sandbox_claude.ps1",
    "Tools/vercel_vcr_setup.ps1",
    "Tools/install_docker.bat",
    "Tools/install_docker_windows.ps1",
    "setup-vercel.bat",
)

# Flags de execucao: o app nasce desbloqueado (padrao de codigo = aberto).
# Aqui so se reporta o que foi ligado/desligado EXPLICITAMENTE na variavel de
# ambiente, porque e a unica coisa que o console declara contra o padrao.
FLAGS_DE_EXECUCAO = (
    "XAU_ENABLE_REAL_ORDERS",
    "XAU_MCP_TRADING",
    "XAU_ENABLE_EMERGENCY_RESUME",
)

# Flags de paper/demo: legais no dia a dia, apenas informative.
FLAGS_DE_DEMO = ("XAU_ENABLE_TRADE_COMMANDS",)

ESTADOS = {"ok": "OK", "aviso": "AVISO", "falha": "FALHA", "pulado": "pulado"}


@dataclass
class Resultado:
    nome: str
    estado: str
    detalhe: str = ""
    dica: str = ""


@dataclass
class Relatorio:
    resultados: list[Resultado] = field(default_factory=list)

    def add(self, resultado: "Resultado") -> None:
        self.resultados.append(resultado)

    @property
    def falhas(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == ESTADOS["falha"]]

    @property
    def avisos(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == ESTADOS["aviso"]]

    def ok_para_operacao_longa(self) -> bool:
        return not self.falhas


# --------------------------------------------------------------------- disco


def checar_disco(minimo_gb: float = DISCO_MINIMO_GB) -> Resultado:
    livre = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if livre < minimo_gb:
        return Resultado(
            "disco livre",
            ESTADOS["falha"],
            f"{livre:.2f} GB (minimo {minimo_gb:.1f} GB)",
            "python scripts/limpeza_segura.ps1 -BuildArtifacts -DebugCache -Apply",
        )
    if livre < minimo_gb * 2:
        return Resultado(
            "disco livre", ESTADOS["aviso"], f"{livre:.2f} GB",
            "opere com cuidado: build Android exige mais espaco",
        )
    return Resultado("disco livre", ESTADOS["ok"], f"{livre:.2f} GB")


# ---------------------------------------------------------------- ferramentas


def checar_ferramentas() -> list[Resultado]:
    resultados = []
    for nome, comando in FERRAMENTAS.items():
        executavel = shutil.which(comando[0])
        if not executavel:
            resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["falha"], "nao encontrada no PATH"))
            continue
        try:
            saida = subprocess.run(
                list(comando), capture_output=True, text=True, timeout=25, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["aviso"], f"erro ao consultar: {exc}"))
            continue
        resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["ok"], saida or executavel))
    return resultados


def checar_python_do_projeto() -> Resultado:
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        return Resultado(
            "python do projeto", ESTADOS["falha"], ".venv/Scripts/python.exe ausente",
            "python -m venv .venv e instale requirements.txt + requirements-dev.txt",
        )
    return Resultado("python do projeto", ESTADOS["ok"], str(python.relative_to(ROOT)))


# ---------------------------------------------------------------------- rede


def porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", porta)) != 0


def checar_portas(esperar_livre: bool) -> list[Resultado]:
    resultados = []
    for nome, porta in PORTAS.items():
        livre = porta_livre(porta)
        if livre:
            resultados.append(Resultado(f"porta {porta} ({nome})", ESTADOS["ok"], "livre"))
        elif esperar_livre:
                resultados.append(
                    Resultado(f"porta {porta} ({nome})", ESTADOS["falha"], "ocupada",
                          "feche o app instalado ou o processo que segura a porta antes de subir outro")
                )
        else:
            resultados.append(
                Resultado(f"porta {porta} ({nome})", ESTADOS["ok"], "ocupada (app em execucao)")
            )
    return resultados


# ------------------------------------------------------------------ git/mql5


def _git(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=40, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def checar_mql5() -> Resultado:
    """MQL5/Experts e intocavel sem autorizacao DECLARADA.

    Qualquer alteracao e bloqueio imediato, SALVO os arquivos listados em
    `AUTORIZACOES_MQL5` — que existe para exigir que a mudanca seja
    rastreavel (autorizacao + commit + motivo), e nao para afrouxar a guarda.

    Antes (03/10/2026) a guarda reprovava qualquer diff. Isso travou uma
    alteracao legitima e medida (cooldown de margem), mas o modo de falha
    oposto e pior: uma guarda que aceita tudo depois de ser "contornada" uma
    vez deixa de valer. Aqui ela continua reprovando o que nao esta declarado.

    Detalhe que importa: o caminho e RELATIVO a `MQL5/Experts`, porque e assim
    que `git status --porcelain -- MQL5/Experts` devolve.
    """
    status, saida = _git("status", "--porcelain", "--", "MQL5/Experts")
    if status != 0:
        return Resultado("guarda MQL5", ESTADOS["aviso"], "nao foi possivel consultar o git")
    if not saida:
        return Resultado("guarda MQL5", ESTADOS["ok"], "MQL5/Experts intacto")

    autorizado = _autorizacoes_mql5()
    nao_declarados: list[str] = []
    declarados: list[str] = []
    for linha in saida.splitlines():
        # Formato do porcelain: "<XY> <caminho>", com XY ocupando 2
        # caracteres e UM espaco de separacao — `linha[3:]` funciona, mas
        # `split(maxsplit=1)` e o que sobrevive a um "\t" no lugar do espaco,
        # que e o mesmo bug de encoding que ja mordeu o dataset e o CSV do
        # forward test.
        partes = linha.split(None, 1)
        if len(partes) != 2:
            # Linha sem caminho (raro, mas nao vale derrubar o preflight).
            nao_declarados.append(linha.strip())
            continue
        caminho = partes[1].strip().strip('"')
        # Normaliza para relativo a MQL5/Experts, como esta no dicionario.
        relativo = caminho
        for prefixo in ("MQL5/Experts/XAU_AI_PRO/", "MQL5/Experts/"):
            if relativo.startswith(prefixo):
                relativo = relativo[len(prefixo):]
                break
        (declarados if relativo in autorizado else nao_declarados).append(caminho)

    if nao_declarados:
        return Resultado(
            "guarda MQL5",
            ESTADOS["falha"],
            f"{len(nao_declarados)} arquivo(s) sem autorizacao: {', '.join(sorted(nao_declarados))}",
            "MQL5 e intocavel: reverta com git checkout -- MQL5/Experts, ou declare a "
            "alteracao em AUTORIZACOES_MQL5 (scripts/preflight.py) com commit e motivo",
        )

    return Resultado(
        "guarda MQL5",
        ESTADOS["aviso"],
        f"{len(declarados)} arquivo(s) com autorizacao declarada: {', '.join(sorted(declarados))}",
        "alteracao MQL5 autorizada: confirme que COMPILOU no MetaEditor64 e "
        "REANEXOU ao grafico antes de tratar como valida",
    )


def checar_git() -> list[Resultado]:
    resultados = []
    status, saida = _git("diff", "--check")
    if status == 0:
        resultados.append(Resultado("git diff --check", ESTADOS["ok"], "sem erro de whitespace"))
    else:
        resultados.append(Resultado("git diff --check", ESTADOS["falha"], saida[:200] or "erro"))
    _, pendentes = _git("status", "--porcelain")
    quantidade = len([linha for linha in pendentes.splitlines() if linha.strip()])
    estado = ESTADOS["aviso"] if quantidade else ESTADOS["ok"]
    resultados.append(Resultado("arquivos pendentes no git", estado, str(quantidade)))
    return resultados


# ------------------------------------------------------------------- limpeza


def checar_scripts_bloqueados() -> Resultado:
    presentes = [rel for rel in SCRIPTS_BLOQUEADOS if (ROOT / rel).exists()]
    if presentes:
        return Resultado(
            "scripts perigosos", ESTADOS["falha"], ", ".join(presentes),
            "esses scripts fazem autoexecucao, limpeza automatica ou baixam binarios em silencio",
        )
    return Resultado("scripts perigosos", ESTADOS["ok"], "nenhum presente")


def checar_binarios_na_raiz() -> Resultado:
    extensoes = {".exe", ".dll", ".vbs", ".scr", ".sys"}
    achados = [p.name for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in extensoes]
    if achados:
        return Resultado(
            "binarios na raiz", ESTADOS["falha"], ", ".join(sorted(achados)),
            "binario solto sombreia o do sistema (ja aconteceu com cmd.exe) e atrai heuristica de AV",
        )
    return Resultado("binarios na raiz", ESTADOS["ok"], "nenhum")


def checar_flags_de_execucao() -> Resultado:
    ligadas = [f for f in FLAGS_DE_EXECUCAO if os.getenv(f) == "1"]
    if ligadas:
        return Resultado(
            "flags de execucao", ESTADOS["falha"], f"explicitas: {', '.join(ligadas)}",
            "o padrao do codigo e aberto; declare a flag so quando quiser divergir do padrao",
        )
    demos = [f for f in FLAGS_DE_DEMO if os.getenv(f) == "1"]
    detalhe = "nenhuma flag explicita (padrao de codigo aberto)"
    if demos:
        detalhe = f"padrao aberto; paper/demo declarado: {', '.join(demos)}"
    return Resultado("flags de execucao", ESTADOS["ok"], detalhe)


def checar_versao() -> Resultado:
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.sync_version import TARGETS, current_version, load_version

        esperado = load_version()
        divergentes = [label for label, path in TARGETS if path.exists() and current_version(path) != esperado]
        if divergentes:
            return Resultado(
                "versao do projeto", ESTADOS["aviso"],
                f"divergente em {len(divergentes)}: {', '.join(divergentes)}",
                "python scripts/sync_version.py",
            )
        return Resultado("versao do projeto", ESTADOS["ok"], esperado)
    except Exception as exc:  # noqa: BLE001 - o preflight nao pode cair
        return Resultado("versao do projeto", ESTADOS["aviso"], f"nao verificada: {exc}")


# ------------------------------------------------------------------- entrada


def executar(etapa: str = "longa") -> Relatorio:
    """Monta o relatorio. `etapa` ajusta o que e bloqueante."""
    relatorio = Relatorio()

    def add(resultado: Resultado) -> None:
        relatorio.resultados.append(resultado)

    minimo = DISCO_MINIMO_ANDROID_GB if etapa == "android" else DISCO_MINIMO_GB
    add(checar_disco(minimo))
    for resultado in checar_ferramentas():
        add(resultado)
    add(checar_python_do_projeto())
    for resultado in checar_portas(esperar_livre=etapa != "app-rodando"):
        add(resultado)
    add(checar_mql5())
    for resultado in checar_git():
        add(resultado)
    add(checar_scripts_bloqueados())
    add(checar_binarios_na_raiz())
    add(checar_flags_de_execucao())
    add(checar_versao())
    return relatorio


def imprimir(relatorio: Relatorio) -> None:
    largura = max((len(r.nome) for r in relatorio.resultados), default=10)
    for r in relatorio.resultados:
        marca = {"OK": "[ ok ]", "AVISO": "[ !! ]", "FALHA": "[XX  ]", "pulado": "[ -- ]"}[r.estado]
        print(f"{marca} {r.nome.ljust(largura)}  {r.detalhe}")
        if r.dica and r.estado in {ESTADOS["falha"], ESTADOS["aviso"]}:
            print(f"        -> {r.dica}")
    print()
    if relatorio.falhas:
        print(f"BLOQUEADO: {len(relatorio.falhas)} falha(s). Corrija antes de comecar a operacao.")
    elif relatorio.avisos:
        print(f"Atencao: {len(relatorio.avisos)} aviso(s), nenhuma falha bloqueante.")
    else:
        print("Tudo pronto para a operacao.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificacao de ambiente do XAU AI PRO (somente leitura)")
    parser.add_argument("--etapa", default="longa", choices=["longa", "android", "app-rodando"],
                        help="ajusta o que e bloqueante: disco minimo e exigencia de portas livres")
    parser.add_argument("--json", action="store_true", help="saida em JSON")
    args = parser.parse_args()

    relatorio = executar(args.etapa)
    if args.json:
        print(json.dumps({
            "ok": relatorio.ok_para_operacao_longa(),
            "itens": [
                {"nome": r.nome, "estado": r.estado, "detalhe": r.detalhe, "dica": r.dica}
                for r in relatorio.resultados
            ],
        }, ensure_ascii=False, indent=2))
    else:
        imprimir(relatorio)
    return 0 if relatorio.ok_para_operacao_longa() else 1


if __name__ == "__main__":
    sys.exit(main())
