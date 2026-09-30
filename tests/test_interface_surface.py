"""Guardas de superfície da interface (frontend).

Leem o código-fonte como TEXTO, e não montando componente, porque são regras
sobre o que está escrito no arquivo: vocabulário de chip e texto de
carregamento. Duas dependências impedem fazer isso do lado do Vitest: o
frontend não tem `@types/node` (sem `fs`) e o pipeline de testes entrega CSS
como string vazia (sem `theme/global.css`).

O que elas protegem, na prática:
- `.chip.neutral` e `.chip.mt5` já estiveram escondidos em
  `theme/history.css`, e o Copiloto (aba Robô) usava aquele tom sem que o
  arquivo do Histórico fossem nem importado por ele;
- rótulo de botão com reticências ASCII (`...`) convivendo com o resto do
  app, que usa `…`.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FRONT_SRC = RAIZ / "frontend" / "src"
COMPONENTES = FRONT_SRC / "components"
GLOBAL_CSS = FRONT_SRC / "theme" / "global.css"

# Ainda não montados pela interface (M4, limpeza de código órfão, ficou fora
# do escopo aprovado): são poupados até essa limpeza acontecer.
NAO_MONTADOS = {"AIControlTab.tsx", "StrategyTesterTab.tsx"}

# Aceita as duas formas de aspas: o tom aparece como `'ok'` em expressao de
# template literal (``chip ${cond ? 'ok' : 'warn'}``) e como `primary` dentro
# de `className="btn sm primary"`. Antes so as aspas simples eram vistas, e o
# tom de botao nunca entrava na contagem.
TONS = re.compile(r"'(ok|warn|danger|neutral|primary|mt5)'|\b(ok|warn|danger|neutral|primary|mt5)\b")
TON_GRUPO = 2  # o grupo 1 cobre as aspas simples, o grupo 2 as sem aspas
RETICENCIAS_ASCII = re.compile(r"\.\.\.'")


def _le(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8", errors="replace")


def _tsx() -> list[Path]:
    return sorted(p for p in COMPONENTES.rglob("*.tsx") if not p.name.startswith("."))


def test_tom_de_chip_usado_existe_no_css_global():
    """Todo tom aplicado via `chip ...` ou `btn ...` tem regra em theme/global.css.

    O scanner olhava so linhas com "chip", e a linha do botao "Aplicar" e
    `className="btn sm primary"` — o tom `primary` existia e era usado, mas
    nao entrava na contagem. Depois da limpeza de 2026-09-29 (que removeu
    ~2.000 linhas de componente morto) nenhum outro `chip primary` sobrou, e
    o teste passou a falhar por causa do proprio scanner, nao por estilo
    faltando. Agora os dois prefixos sao lidos.
    """
    usados: dict[str, str] = {}
    for arquivo in _tsx():
        for linha in _le(arquivo).splitlines():
            # `chip mt5` e tom de chip; `btn primary` e tom de botao. Um
            # mesmo nome de tom nas duas familias nao e a mesma regra: `mt5`
            # so existe como `.chip.mt5` e nao como `.btn.mt5`. Por isso o
            # prefixo precisa sair da propria linha, e nao de uma busca ampla.
            if "chip" in linha:
                for _, tom in TONS.findall(linha):
                    usados.setdefault(f"chip.{tom}", "chip")
            if "btn" in linha:
                # `className="btn ..."` e classe; `broker === 'mt5'` e um valor
                # comparado dentro de um handler e nao vira tom de botao. O
                # nome do tom so conta quando vem da propria lista de classes.
                classes = re.search(r'className\s*=\s*"([^"]*)"', linha)
                if not classes:
                    continue
                for _, tom in TONS.findall(classes.group(1)):
                    usados.setdefault(f"btn.{tom}", "btn")

    # Se o scanner parar de enxergar, o teste tem de ser consertado — não
    # deixado passar em silêncio com um conjunto vazio. O piso e 5 porque e
    # o menor conjunto que ainda prova as duas familias: 4 tons de chip
    # (ok/warn/danger/neutral) e pelo menos um de botao (primary).
    assert len(usados) >= 5, f"scanner de tons quebrou: {sorted(usados)}"
    assert any(k.startswith("btn.") for k in usados), (
        f"nenhum tom de botao lido; o scanner so esta vendo chip: {sorted(usados)}"
    )

    # `usados` ja guarda a chave completa no formato que o CSS usa
    # (`.chip.ok`, `.btn.primary`), entao a busca e literal.
    css = _le(GLOBAL_CSS)
    faltando = sorted(seletor for seletor in usados if f".{seletor}" not in css)
    assert not faltando, f"tons usados sem regra em global.css: {faltando}"


def test_rotulo_de_carregamento_nao_usa_reticencias_ascii():
    """O app inteiro usa `…`; três pontinhos sobraram só em dois componentes."""
    faltando: list[str] = []
    for arquivo in _tsx():
        if arquivo.name in NAO_MONTADOS:
            continue
        for numero, linha in enumerate(_le(arquivo).splitlines(), start=1):
            if RETICENCIAS_ASCII.search(linha):
                faltando.append(f"{arquivo.name}:{numero}")

    assert not faltando, f"rotulo com reticencias ASCII: {faltando}"


def test_estado_vazio_tem_classe_com_css():
    """`empty-state` nao tem nenhuma regra; `placeholder` tem."""
    css = _le(FRONT_SRC / "theme" / "global.css")
    assert ".placeholder {" in css

    sem_estilo = [
        arquivo.name
        for arquivo in _tsx()
        if 'className="empty-state"' in _le(arquivo)
    ]
    assert not sem_estilo, f"estado vazio sem CSS: {sem_estilo}"
