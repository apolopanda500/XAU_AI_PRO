# -*- coding: utf-8 -*-
"""Sincroniza o design system da Figma para os tokens do CSS.

POR QUE ISTO EXISTE
===================
O projeto tem 8 temas e ~30 tokens escritos a mao em `theme/global.css`.
Mudar um verde significava editar CSS, e a Figma continuava com o valor
antigo: duas fontes de verdade divergindo em silencio.

Aqui a Figma e a fonte e o CSS e gerado a partir dela.

AS DUAS PORTAS, E POR QUE SAO DUAS
==================================
1. `FIGMA_TOKEN` + `FIGMA_FILE_KEY` (API REST): le variaveis, estilos e
   componentes. Variaveis exigem plano Professional; sem ele, o endpoint
   responde 403 e este modulo cai para os outros dois.
2. O MCP remoto (`mcp.figma.com`), por OAuth. E por onde a IA LE o design
   system no dia a dia. Nao usa a mesma credencial.

O QUE NAO E FEITO
=================
- Nao inventa valor: se a Figma nao tem `bg`, o modulo nao escreve `bg`.
- Nao apaga o que existe: gera `figma-tokens.css`, que sobrescreve SO o que a
  Figma define. O CSS mao continua valendo para o que ainda nao foi para a
  Figma.
- Nao chama a API em loop: e leitura sob demanda, por comando.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\sincronizar_figma.py
    .\\.venv\\Scripts\\python.exe scripts\\sincronizar_figma.py --aplicar
    .\\.venv\\Scripts\\python.exe scripts\\sincronizar_figma.py --verificar
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
DESTINO = RAIZ / "frontend" / "src" / "theme" / "figma-tokens.css"
API = "https://api.figma.com/v1"

# Os 8 temas do projeto viram modos da Figma. Este mapa amarra os dois lados:
# `cor/xau_dark/bg` vira `[data-theme="xau"] { --bg: ... }` no CSS.
# As duas chaves de cada tema sao aceitas: o nome do CSS (`xau_dark`) e o
# apelido curto do roteiro (`xau`). Assim o design system pode ser montado
# com qualquer um dos dois e o resultado e o mesmo.
TEMAS = ("dark", "xau_dark", "btc_dark", "light", "ocean_dark",
         "emerald_dark", "rose_dark", "violet_dark")
MODOS = {
    "dark": "dark", "xau_dark": "xau", "btc_dark": "btc", "light": "light",
    "ocean_dark": "ocean", "emerald_dark": "emerald", "rose_dark": "rose",
    "violet_dark": "violet",
    "xau": "xau", "btc": "btc", "ocean": "ocean", "emerald": "emerald",
    "rose": "rose", "violet": "violet",
}
def ler_do_env(nome: str) -> str:
    if not ENV.exists():
        return ""
    prefixo = nome + "="
    for linha in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith(prefixo):
            return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def chamar(rota: str, token: str) -> tuple[int, Any]:
    requisicao = urllib.request.Request(
        API + rota, headers={"X-Figma-Token": token, "User-Agent": "XAU_AI_PRO"}
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            return resposta.status, json.loads(resposta.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as erro:
        try:
            return erro.code, json.loads(erro.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return erro.code, {}
    except Exception:  # noqa: BLE001
        return 0, {}


def rgba_para_hex(valor: Any) -> str:
    """`{r,g,b,a}` da Figma -> `#rrggbb`. Alpha parcial vira canal `alpha`.

    A Figma guarda cor como objeto com canais de 0 a 1; o CSS quer hex.
    Fazer a conversao aqui, e nao no CSS, mantem o arquivo gerado legivel.
    """
    if not isinstance(valor, dict):
        return ""
    canais = [float(valor.get(c, 0) or 0) for c in ("r", "g", "b")]
    if any(c > 1 for c in canais):
        canais = [c / 255.0 for c in canais]
    r, g, b = (max(0, min(255, round(c * 255))) for c in canais)
    hexa = f"#{r:02x}{g:02x}{b:02x}"
    alpha = float(valor.get("a", 1) or 1)
    return hexa if alpha >= 0.999 else f"{hexa} / {round(alpha, 3)}"


def valor_para_css(valor: Any) -> str:
    if isinstance(valor, dict):
        if "r" in valor:
            return rgba_para_hex(valor)
        if "value" in valor:
            return str(valor["value"])
    return str(valor)


def ler_variaveis(token: str, file_key: str) -> tuple[dict[str, Any], str]:
    """Le as variaveis. Devolve (mapa, motivo_da_falha)."""
    status, dados = chamar(f"/files/{file_key}/variables/local", token)
    if status == 200:
        return dados.get("meta", {}).get("variables", {}) or {}, ""
    mensagem = str(dados.get("message") or "")
    if "file_variables:read" in mensagem:
        return {}, (
            "a API de variaveis exige o escopo file_variables:read E plano "
            "Professional. O escopo NAO aparece na lista de recusados da Figma, "
            "logo o bloqueio e de plano, nao de permissao."
        )
    return {}, f"variaveis: HTTP {status}"


def ler_estilos(token: str, file_key: str) -> tuple[list[dict], str]:
    status, dados = chamar(f"/files/{file_key}/styles", token)
    if status != 200:
        return [], f"estilos: HTTP {status}"
    return dados.get("meta", {}).get("styles", []) or [], ""


CABECALHO = """/* ==========================================================
 * TOKENS GERADOS DA FIGMA — NAO EDITE COM A MAO
 * ==========================================================
 * Fonte: Figma (variaveis e estilos do design system publicado).
 * Gerador: scripts/sincronizar_figma.py
 *
 * Para mudar um valor, mude NA FIGMA e rode o script de novo.
 * Edicao manual aqui e sobrescrita na proxima sincronizacao.
 *
 * Este arquivo define SO o que existe na Figma. O que nao estiver
 * aqui continua vindo de global.css.
 * ========================================================== */
"""


def gerar_css(variaveis: dict, estilos: list[dict]) -> str:
    """Monta o CSS. So escreve o que a Figma de fato define."""
    linhas = [CABECALHO]
    base: dict[str, str] = {}
    modos: dict[str, dict[str, str]] = {}

    for var in variaveis.values():
        nome = str(var.get("name", "")).strip()
        if "/" not in nome:
            continue
        partes = [p.strip().lower().replace(" ", "-") for p in nome.split("/") if p.strip()]
        if len(partes) < 2:
            continue

        # A Figma guarda o TEMA como "modo" da variavel (`valuesByMode`), e o
        # caminho do nome guarda o PAPEL. Entao `cor/dark/bg` tem 3 partes:
        # a primeira e a familia, a segunda e o tema, a terceira e o papel.
        #
        # A primeira versao deste parser usava `partition` e produzia
        # `--1: 4` e `[data-theme="default"] { --dark: ... }`: os nomes
        # saiam trocados e o CSS gerado nao servia para nada. O teste com
        # variaveis falsas pegou isso antes de qualquer arquivo ser gravado.
        familia, resto = partes[0], partes[1:]

        # O tema, quando existe, e o unico segmento que o mapa reconhece.
        # Acha-lo pelo mapa, e nao pela posicao, e o que faz o parser
        # funcionar com `cor/dark/bg` e com `cor/xau_dark/bg` sem mudanca.
        modo = ""
        for parte in resto[:-1]:
            if parte in MODOS:
                modo = MODOS[parte]
                break
        # `espaco/1` -> papel "1", que geraria `--1` e nao serve. Quando o
        # papel comeca com digito, junta com a familia: `espaco/1` -> `espaco-1`.
        papel = resto[-1]
        if papel.isdigit() or papel[0].isdigit():
            papel = f"{familia}-{papel}"
        _ = modo

        valores = dict(var.get("defaultValueByMode") or {})
        valores.update(var.get("valuesByMode") or {})
        for nome_modo, valor in valores.items():
            texto = valor_para_css(valor)
            if not texto:
                continue
            # O TEMA vem de DOIS lugares, e a Figma usa os dois:
            #  1. do modo da variavel (`valuesByMode: {xau: ...}`) — e o caso comum
            #  2. do proprio nome da variavel (`cor/xau_dark/bg`) — quando o time
            #     organiza por pasta em vez de por modo
            #
            # A primeira versio ignorava o item 2 e tratava `xau_dark` (do nome)
            # como se fosse `default`: o tema virava valor padrao, e o CSS gerado
            # tinha o valor certo em `:root` e nenhum `[data-theme]`. O teste com
            # variaveis falsas pegou isso antes de qualquer arquivo ser gravado.
            bruto_modo = str(nome_modo).strip().lower().replace(" ", "-")
            modo_real = MODOS.get(bruto_modo, bruto_modo)
            if modo and modo_real in ("default", ""):
                modo_real = modo
            if modo_real in ("default", ""):
                base[papel] = texto
            else:
                modos.setdefault(papel, {})[modo_real] = texto

    # `:root` e SEMPRE emitido, mesmo vazio. Sem isso, quando toda variavel tem
    # tema no nome (`cor/dark/bg`), nao existe `:root` algum — e o arquivo
    # gerado perde o seletor de fallback do app. O teste pegou isso.
    linhas.append(":root {")
    for chave in sorted(base):
        linhas.append(f"  --{chave}: {base[chave]};")
    linhas.append("}")
    linhas.append("")

    for papel, por_modo in sorted(modos.items()):
        for modo, texto in sorted(por_modo.items()):
            linhas.append(f'[data-theme="{modo}"] {{')
            linhas.append(f"  --{papel}: {texto};")
            linhas.append("}")
        linhas.append("")

    if estilos:
        nomes = sorted({str(s.get("name", "")).strip() for s in estilos if s.get("name")})
        linhas.append("/* Estilos publicados na Figma */")
        for nome in nomes:
            linhas.append(f"/*   - {nome} */")
        linhas.append("")
    return "\n".join(linhas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza Figma -> CSS")
    parser.add_argument("--aplicar", action="store_true", help="grava o CSS")
    parser.add_argument("--verificar", action="store_true", help="so compara")
    args = parser.parse_args()

    token = ler_do_env("FIGMA_TOKEN")
    file_key = ler_do_env("FIGMA_FILE_KEY")
    if not token or not file_key:
        print("[FALHA ] falta FIGMA_TOKEN ou FIGMA_FILE_KEY no .env")
        return 1

    variaveis, aviso_var = ler_variaveis(token, file_key)
    estilos, aviso_est = ler_estilos(token, file_key)
    print(f"variaveis: {len(variaveis)}")
    if aviso_var:
        print(f"  {aviso_var}")
    print(f"estilos:   {len(estilos)}")
    if aviso_est:
        print(f"  {aviso_est}")

    if not variaveis and not estilos:
        print()
        print("[INFO  ] a Figma nao devolveu variaveis nem estilos: o design")
        print("        system ainda nao foi criado/publicado nela.")
        print("        Roteiro: docs/FIGMA_DESIGN_SYSTEM.md")
        return 1

    css = gerar_css(variaveis, estilos)
    if args.verificar:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        print()
        print("IGUAL ao arquivo atual" if atual == css else "DIVERGENTE")
        return 0 if atual == css else 2
    if args.aplicar:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        DESTINO.write_text(css, encoding="utf-8")
        print(f"[ ok ] {DESTINO.relative_to(RAIZ)} gerado")
        return 0
    print("\n rode com --aplicar para gravar, ou --verificar para comparar")
    return 0


if __name__ == "__main__":
    sys.exit(main())