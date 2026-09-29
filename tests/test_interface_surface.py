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

TONS = re.compile(r"'(ok|warn|danger|neutral|primary|mt5)'")
RETICENCIAS_ASCII = re.compile(r"\.\.\.'")


def _le(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8", errors="replace")


def _tsx() -> list[Path]:
    return sorted(p for p in COMPONENTES.rglob("*.tsx") if not p.name.startswith("."))


def test_tom_de_chip_usado_existe_no_css_global():
    """Todo tom aplicado via `chip ${...}` tem regra em theme/global.css."""
    usados: set[str] = set()
    for arquivo in _tsx():
        for linha in _le(arquivo).splitlines():
            if "chip" in linha:
                usados.update(TONS.findall(linha))

    # Se o scanner parar de enxergar, o teste tem de ser consertado — não
    # deixado passar em silêncio com um conjunto vazio.
    assert len(usados) >= 5, f"scanner de tons quebrou: {sorted(usados)}"

    css = _le(GLOBAL_CSS)
    faltando = sorted(tom for tom in usados if f".chip.{tom}" not in css)
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
