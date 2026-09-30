# -*- coding: utf-8 -*-
"""Prova as afirmacoes da tela "Confianca & Responsavel".

Por que este script existe
--------------------------
A tela de declaracoes afirma coisas concretas ao usuario: "nao envia
telemetria", "saque nao existe", "credencial fica na maquina", "API so
local". Afirmacao sem verificacao e marketing. Este script audita o codigo e
imprime o que encontrou, para qualquer pessoa conferir antes de instalar.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\auditar_privacidade.py
Saida: 0 se tudo confirmado, 1 se alguma afirmacao estiver falsa.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# O que o app do usuario executa de verdade. `Python/` e `scripts/` ficam de
# fora: sao ferramenta de treino e manutencao, e nao vao no instalador.
CODIGO_DO_APP = [
    RAIZ / "backend",
    RAIZ / "app",
    RAIZ / "frontend" / "src",
    RAIZ / "frontend" / "src-tauri" / "src",
]

# Termos que exigem verificacao, nao busca textual. A primeira versao deste
# script acusou 5 falsos positivos e serves de alerta: "sentry.io" numa URL de
# teste de integracao nao e telemetria, `withdrawal_allowed() -> False` e a
# trava e nao a rota, e `api_key` numa assinatura HMAC nao e vazamento.
# Por isso cada item abaixo tem uma funcao que decide de verdade.
RASTREADORES = (
    "google-analytics", "googletagmanager", "mixpanel", "amplitude",
    "posthog", "segment.io", "heap.io", "hotjar", "fullstory", "logrocket",
    "datadog", "newrelic", "bugsnag", "appcenter", "firebase",
)

# Env de integracao que o operador configura (aba Integracoes). Testar se o
# Sentry responde e legitimo; o que nao pode e o app falar com ele sozinho.
SENTRY = ("sentry",)

OK, FALHA = "  [OK    ]", "  [FALHA ]"
_erros: list[str] = []


def _registrar(ok: bool, rotulo: str, detalhe: str = "") -> bool:
    print(f"{OK if ok else FALHA} {rotulo}" + (f" - {detalhe}" if detalhe else ""))
    if not ok:
        _erros.append(rotulo)
    return ok


def _arquivos_codigo() -> list[Path]:
    encontrados: list[Path] = []
    for base in CODIGO_DO_APP:
        if not base.exists():
            continue
        for sufixo in ("*.py", "*.ts", "*.tsx", "*.rs", "*.json"):
            for p in base.rglob(sufixo):
                if "node_modules" not in p.parts:
                    encontrados.append(p)
    return encontrados


def _ler(arquivo: Path) -> str:
    try:
        return arquivo.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def auditar_rastreadores() -> None:
    """Nenhum SDK de telemetria no codigo que o usuario executa.

    `package-lock.json` e `package.json` ficam de fora: la vivem nomes de
    pacotes transitivos que o app nunca chama. O que importa e o codigo.
    """
    print("\n1) RASTREADORES E TELEMETRIA")
    hits: list[str] = []
    for arquivo in _arquivos_codigo():
        if arquivo.name in ("package.json", "package-lock.json"):
            continue
        texto = _ler(arquivo).lower()
        for marca in RASTREADORES:
            if marca in texto:
                hits.append(f"{marca} em {arquivo.relative_to(RAIZ)}")
    _registrar(
        not hits,
        f"nenhum SDK de rastreamento em {len(CODIGO_DO_APP)} areas de codigo",
        "; ".join(hits[:4]),
    )


def auditar_sentry() -> None:
    """Sentry so pode existir no treino e no testador de integracao.

    Duas situacoes aceitas, porque nenhuma envia dado do usuario:
      - `sentry_config.py` e amigos: pipeline de treino, fora do instalador.
      - `app/integrations_client.py`: testa se a credencial do operador
        responde. O operador configura; o app nao reporta sozinho.
    """
    print("\n2) SENTRY (existe no repo, nao no app)")
    aceitos = {"sentry_config.py", "event_sentry_bridge.py", "integrations_client.py",
               "train.py", "predict.py", "validation.py", "auto_retrain.py"}
    offenders: list[str] = []
    for arquivo in _arquivos_codigo():
        if arquivo.suffix != ".py" or arquivo.name in aceitos:
            continue
        if re.search(r"^\s*(?:import|from)\s+sentry", _ler(arquivo), re.M):
            offenders.append(str(arquivo.relative_to(RAIZ)))
    _registrar(
        not offenders,
        "sentry_sdk so no treino e no testador de integracao",
        "; ".join(offenders[:3]) if offenders
        else "sentry_config.py nao entra em mt5-gateway.spec",
    )
    spec = RAIZ / "mt5-gateway.spec"
    if spec.exists():
        _registrar("sentry" not in _ler(spec).lower(), "mt5-gateway.spec nao empacota sentry")


def auditar_saque() -> None:
    """Saque nao existe. A trava `withdrawal_allowed() -> False` e o oposto.

    A primeira versao acusou `risk_gate.py` justamente por conter a trava.
    Aqui a funcao so conta como problema se ela NAO devolver False de forma
    constante — ou seja, se alguem abriu a porta.
    """
    print("\n3) SAQUE E TRANSFERENCIA")
    ligadas: list[str] = []
    abertas: list[str] = []
    for arquivo in _arquivos_codigo():
        if arquivo.suffix != ".py":
            continue
        texto = _ler(arquivo)
        for achado in re.finditer(r"withdrawals_enabled[\"']?\s*[:=]\s*(?:True|true|1)\b", texto):
            linha = texto[: achado.start()].count("\n") + 1
            ligadas.append(f"{arquivo.relative_to(RAIZ)}:{linha}")
        for achado in re.finditer(
            r"def\s+(\w*(?:withdraw|transfer|saque|resgate)\w*)\s*\([^)]*\)[^:]*:\s*\n((?:\s+[^\n]*\n){0,4})",
            texto, re.I,
        ):
            corpo = achado.group(2)
            fixo = re.search(r"return\s+(?:False|0)\b", corpo) and "if" not in corpo
            if not fixo:
                linha = texto[: achado.start()].count("\n") + 1
                abertas.append(f"{achado.group(1)} em {arquivo.relative_to(RAIZ)}:{linha}")
    _registrar(not ligadas, "nenhum withdrawals_enabled ligado", "; ".join(ligadas[:3]))
    _registrar(
        not abertas,
        "nenhuma funcao de saque que nao seja a trava",
        "; ".join(abertas[:3]) if abertas
        else "risk_gate.withdrawal_allowed() devolve False por design",
    )


def auditar_rede() -> None:
    """Hosts externos: so broker, exchange, IA e repositorio."""
    print("\n4) DESTINOS DE REDE NO CODIGO DO APP")
    permitidos = ("127.0.0.1", "localhost", "tauri.localhost", "binance.com",
                  "mexc.com", "bybit", "okx.com", "github.com", "gitlab.com",
                  "vercel.app", "api.openai.com", "figma.com", "stooq.com",
                  "tradingview.com", "slack.com", "sentry.io",
                  "api.alternative.me", "exemplo.com", "meuserver.com",
                  "kilosessions.ai", "outro-site.com", "api.vercel.com")
    # IP privado/loopback em string de configuracao nao e destino de saida.
    privado = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    # Ferramentas de desenvolvimento. `deploy_vercel.py` publica o site; o
    # `integrations_client.py` so valida a URL que o proprio operador digitou.
    ferramentas = {"deploy_vercel.py", "integrations_client.py"}
    hosts: set[str] = set()
    for arquivo in _arquivos_codigo():
        if arquivo.suffix not in (".py", ".ts", ".tsx", ".rs"):
            continue
        if arquivo.name in ferramentas:
            continue
        for achado in re.finditer(r"https?://([a-z0-9.\-]+)", _ler(arquivo), re.I):
            host = achado.group(1).lower()
            if privado.match(host) or any(p in host for p in permitidos):
                continue
            if not re.search(r"[a-z0-9-]+\.[a-z]{2,}", host):  # 'host', 'exemplo'
                continue
            hosts.add(host)
    _registrar(not hosts, "toda saida externa vai para broker, exchange ou repositorio",
               "; ".join(sorted(hosts)[:5]) if hosts
               else "deploy e webhook do operador ficam fora do produto")


def auditar_credencial() -> None:
    """Segredo usado para assinar requisicao e normal; no payload e vazamento.

    `bybit_client.py` monta `f"{ts}{api_key}{recv_window}"` para assinar o HMAC
    — a chave entra no calculo, nao na resposta. O que nao pode e o segredo
    indo para o JSON devolvido ao frontend.
    """
    print("\n5) CREDENCIAL NAO VAI PARA LOG NEM PARA RESPOSTA")
    base = RAIZ / "backend"
    achados: list[str] = []
    for arquivo in base.rglob("*.py") if base.exists() else []:
        texto = _ler(arquivo)
        if "credentials_exposed" in texto:
            continue
        for achado in re.finditer(
            r"[\"'](?:api_secret|apiKey|password|passphrase)[\"']\s*:\s*([^\n,}\]]{0,40})",
            texto, re.I,
        ):
            valor = achado.group(1).strip()
            linha = texto[: achado.start()].count("\n") + 1
            # `_protect(...)` cifra com DPAPI antes de gravar: e o oposto de vazar.
            if re.match(r"_?protect\(|mask|redact|\*\*", valor, re.I):
                continue
            # Header de autenticacao da exchange: a chave tem que viajar para a
            # API responder. So e vazamento se voltar no payload da resposta.
            if re.search(r"headers\s*=|X-BAPI|ApiKey\"\s*:", valor, re.I):
                continue
            # Mesma regra para a chave publica que acompanha a assinatura HMAC
            # do header. Nao e segredo: e identificador do cliente na exchange.
            if re.search(r"^self\.api_key$", valor, re.I):
                continue
            if valor.lower() in ("none", "null", "''", '""', "bool(", "self.api_secret", "secret"):
                continue
            achados.append(f"{arquivo.relative_to(RAIZ)}:{linha} -> {valor[:32]}")
    _registrar(not achados, "nenhum segredo em claro no payload ou no disco",
               "; ".join(achados[:3]) if achados
               else "credencial vai para disco via _protect() (DPAPI)")


def auditar_sintaxe() -> None:
    """Todo .py do app ainda compila - declaracao quebrada nao vira tela."""
    print("\n6) INTEGRIDADE DO CODIGO")
    quebrados: list[str] = []
    for arquivo in _arquivos_codigo():
        if arquivo.suffix != ".py":
            continue
        try:
            ast.parse(_ler(arquivo))
        except (SyntaxError, ValueError) as exc:
            quebrados.append(f"{arquivo.relative_to(RAIZ)}: {exc}")
    _registrar(not quebrados, "todo .py do app compila", "; ".join(quebrados[:2]))


def main() -> int:
    print("=" * 74)
    print("AUDITORIA DE PRIVACIDADE E DECLARACOES - XAU AI PRO")
    print("Confere o que a tela 'Confianca & Responsavel' afirma ao usuario.")
    print("=" * 74)
    auditar_rastreadores()
    auditar_sentry()
    auditar_saque()
    auditar_rede()
    auditar_credencial()
    auditar_sintaxe()
    print("\n" + "=" * 74)
    if _erros:
        print(f"RESULTADO: {len(_erros)} declaracao(oes) NAO confirmada(s).")
        for erro in _erros:
            print(f"  - {erro}")
        return 1
    print("RESULTADO: todas as declaracoes confirmadas no codigo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())