"""Gera a folha de estilos para copiar na Figma, a partir do CSS real.

Existe para que ninguem digite hexadecimal de memoria: os valores sao lidos
do `global.css`, entao a folha e a fonte — se o CSS mudar, a folha muda com
ele. Um documento mantido a mao divergiria em silencio, que e o defeito que
esta folha existe para evitar.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\gerar_folha_figma.py
"""
import re, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CSS = RAIZ / "frontend" / "src" / "theme" / "global.css"
SAIDA = RAIZ / "docs" / "FOLHA_ESTILOS_FIGMA.md"

TEMAS = ["dark", "xau_dark", "btc_dark", "light", "ocean_dark",
         "emerald_dark", "rose_dark", "violet_dark"]
# O rotulo curto e o que o sincronizador gera em `[data-theme="..."]`.
CURTO = {"xau_dark": "xau", "btc_dark": "btc", "light": "light",
         "ocean_dark": "ocean", "emerald_dark": "emerald",
         "rose_dark": "rose", "violet_dark": "violet", "dark": "dark"}
ORDEM = ["bg", "panel", "panel2", "border", "text", "muted",
         "primary", "primary-contrast", "ok", "warn", "danger"]

def main() -> int:
    t = CSS.read_text(encoding="utf-8")
    base = {}
    # O parser le ate o proximo `}` CONTANDO o nivel de chave. Um `.*?` sem
    # contar nivel para no fechamento errado e o tema seguinte desaparece do
    # mapa sem erro — foi assim que `xau_dark` e `btc_dark` sairam da folha
    # com "-" sendo que o CSS estava certo.
    #
    # O seletor pode ser AGRUPADO (`[data-theme='xau_dark'],` seguido de
    # `[data-theme='xau'] {`), entao todos os nomes do grupo entram. E o
    # mapa ACUMULA: `base[nome] = ...` sobrescreveria, e o tema perderia
    # variavel quando aparecesse em dois blocos.
    grupo = r"((?:\[data-theme='[a-z_]+'\]\s*,\s*)*\[data-theme='[a-z_]+'\])\s*\{"
    for m in re.finditer(grupo, t):
        nomes = re.findall(r"\[data-theme='([a-z_]+)'\]", m.group(1))
        i, nivel = m.end(), 1
        while i < len(t) and nivel:
            if t[i] == "{":
                nivel += 1
            elif t[i] == "}":
                nivel -= 1
            i += 1
        variaveis = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", t[m.end():i]))
        for nome in nomes:
            base.setdefault(nome, {}).update(variaveis)
    raiz = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);",
                           re.search(r":root\s*\{(.*?)\n\}", t, re.S).group(1)))
    base["_root"] = raiz

    L = []
    L.append("# Folha de estilos para a Figma\n")
    L.append("> **GERADA.** Fonte: `frontend/src/theme/global.css`. "
             "Gerador: `scripts/gerar_folha_figma.py`.\n")
    L.append("> Nao edite a mao: se o CSS mudar, rode o gerador de novo.\n")
    L.append("\n## Como criar na Figma\n")
    L.append("1. No arquivo, abra **Styles** (o icone de pincel) e clique em **+**.")
    L.append("2. Crie uma **Variable collection** chamada `Cor`.")
    L.append("3. Crie uma variavel por papel, com os modos na ordem:\n")
    L.append("   | Variavel | " + " | ".join(CURTO[t] for t in TEMAS) + " |")
    L.append("   |---|" + "---|" * len(TEMAS))
    for papel in ORDEM:
        # `TEMAS` traz `xau_dark`; no CSS o bloco chama-se `[data-theme='xau_dark']`.
        # A coluna usa o apelido curto, entao o valor e lido pelo nome LONGO.
        cel = [base.get(t, {}).get(papel) or raiz.get(papel, "-") for t in TEMAS]
        L.append(f"   | `{papel}` | " + " | ".join(cel) + " |")
    L.append("\n## Espacamento e densidade (variaveis `NUMBER`)\n")
    L.append("| Variavel | Valor | Onde e usado |")
    L.append("|---|---|---|")
    uso = {"space/1": "gap minimo", "space/2": "gap pequeno",
           "space/3": "gap medio", "space/4": "gap grande",
           "space/5": "separacao de bloco", "space/6": "separacao de secao",
           "densidade/linha-compacta": "linha de tabela densa",
           "densidade/linha-normal": "linha de tabela normal",
           "densidade/linha-confortavel": "linha de tabela com folga",
           "alvo/minimo": "altura minima de botao",
           "raio/painel": "cantos do painel", "raio/pequeno": "botao e chip"}
    for k, v in raiz.items():
        if k.startswith("space-") or k.startswith("row-h") or k in ("hit-min", "radius", "radius-sm"):
            nome = k.replace("space-", "space/").replace("row-h-", "densidade/linha-")
            nome = nome.replace("hit-min", "alvo/minimo").replace("radius", "raio")
            if nome == "raio": nome = "raio/painel"
            elif nome == "raio-sm": nome = "raio/pequeno"
            L.append(f"| `{nome}` | {v.strip()} | {uso.get(nome, '')} |")
    L.append("\n## O que o gerador faz com isto\n")
    L.append("```powershell")
    L.append(".\\.venv\\Scripts\\python.exe scripts\\sincronizar_figma.py --aplicar")
    L.append("```")
    L.append("\nEle gera `frontend/src/theme/figma-tokens.css`, que o `main.tsx` importa "
             "**por ultimo** — e por isso que o valor da Figma vence o CSS manual.\n")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"folha gerada: {SAIDA.relative_to(RAIZ)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
