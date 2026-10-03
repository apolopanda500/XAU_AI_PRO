# -*- coding: utf-8 -*-
"""O `.spec` do PyInstaller nao pode esquecer modulo nenhum.

O QUE ACONTECEU (2026-10-02)
===========================
`backend/metas_vip.py` e `backend/acesso.py` foram criados e os testes
passaram (712 green, 22 deles sobre as metas). O build passou. O instalador
passou. E o app instalado subiu **sem nenhum dos dois**.

Causa: `mt5-gateway.spec` empacota os modulos do backend por lista explicita
em `hiddenimports`. Modulo novo que nao entrar na lista NAO vai no bundle — e
o `.spec` tem um comentario que ja descreve esse exato modo de falha para
outros modulos ("o app instalado mostrava modelos nao carregam").

Por que ninguem viu: a suite roda contra o FONT, nao contra o executavel
empacotado. `pytest` importa `backend.metas_vip` do disco e passa. O
PyInstallerWorkingSet nao tem o arquivo e o app sobe sem ele. **Nenhum teste
do projeto cobria essa distancia.**

Este teste fecha essa distancia sem empacotar: ele descobre todo modulo
`backend/*.py` do fonte e exige que cada um esteja em `hiddenimports`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SPEC = RAIZ / "mt5-gateway.spec"
BACKEND = RAIZ / "backend"


def _hidden_imports_do_spec() -> set[str]:
    """Modulos declarados em `hiddenimports` no `.spec`.

    Le o arquivo em vez de importa-lo: o `.spec` e um script PyInstaller com
    nomes de classe em caixa alta (`Analysis`, `PYZ`, `EXE`), nao um modulo
    Python comum, e `exec` dele exigiria o namespace do PyInstaller.
    """
    texto = SPEC.read_text(encoding="utf-8")
    bloco = re.search(r"hiddenimports=\[(.*?)\]", texto, re.DOTALL)
    assert bloco is not None, "mt5-gateway.spec nao tem hiddenimports=[...]"
    return set(re.findall(r"'([^']+)'", bloco.group(1)))


#: Modulos que o PyInstaller JA pega sozinho por serem importados no nivel
#: superior de `backend/mt5_gateway.py`. Eles nao precisam estar na lista, e
#: o teste abaixo nao os exige — exigir seria errado e ensinaria a listar
#: duas vezes o mesmo modulo.
#
#: Verificado com:
#:   git grep -n "^from backend.<m> import" -- backend/mt5_gateway.py
IMPORTADOS_NO_TOPO: frozenset[str] = frozenset({
    "backend.binance_client",
    "backend.bybit_client",
    "backend.mexc_client",
    "backend.okx_client",
})


def _modulos_do_backend() -> set[str]:
    """Todo `backend/<modulo>.py` do fonte que precisa estar no bundle."""
    return {
        f"backend.{p.stem}"
        for p in BACKEND.glob("*.py")
        if p.stem != "__init__" and f"backend.{p.stem}" not in IMPORTADOS_NO_TOPO
    }


def test_spec_existe():
    assert SPEC.exists(), f"spec ausente: {SPEC}"


def test_nenhum_modulo_do_backend_fica_de_fora_do_bundle():
    """O teste que teria pegado o bug do VIP.

    Um modulo em `backend/` que nao esta em `hiddenimports` simplesmente nao
    existe dentro do `.exe` instalado. O sintoma do usuario e "a tela nao
    mostra", e nao ha excecao em lugar nenhum: o app sobe normal.
    """
    declarados = _hidden_imports_do_spec()
    esquecidos = sorted(_modulos_do_backend() - declarados)
    assert not esquecidos, (
        "modulos de backend/ fora do hiddenimports do mt5-gateway.spec — "
        "o app instalado vai subir sem eles, sem erro visivel:\n  "
        + "\n  ".join(esquecidos)
    )


def test_modulos_do_vip_estao_declarados():
    """Trava especifica: os modulos do VIP deste ciclo."""
    declarados = _hidden_imports_do_spec()
    for modulo in ("backend.metas_vip", "backend.acesso", "backend.vip_progress"):
        assert modulo in declarados, (
            f"{modulo} ausente do hiddenimports. O app instalado sobe sem ele."
        )


@pytest.mark.parametrize("modulo", ["backend.metas_vip", "backend.acesso"])
def test_modulo_existe_no_fonte(modulo: str):
    """O `__name__` precisa bater com um arquivo real."""
    caminho = RAIZ / (modulo.replace(".", "/") + ".py")
    assert caminho.exists(), f"{modulo} declarado no spec mas sem arquivo: {caminho}"


# ---------------------------------------------------------------------------
# MODELOS: o `.pkl` nao e modulo, entao `hiddenimports` nao o alcança
# ---------------------------------------------------------------------------


def _datas_do_spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_pasta_de_modelos_entra_no_bundle():
    """O `.pkl` e dado, nao modulo: so entra em `datas`.

    `ai_inference` carrega o modelo com `joblib.load` em tempo de execucao.
    O PyInstaller so enxerga modulo importado, entao a pasta de modelos so
    entra pelo par `(origem, destino)` em `datas`. Sem ele o instalador compila
    sem erro e sai SEM os modelos — o app instalado apenas mostra
    "modelos nao carregam", sem excecao em lugar nenhum.
    """
    assert re.search(
        r'datas\.append\(\("frontend/src-tauri/Python/models",\s*"Python/models"\)\)',
        _datas_do_spec(),
    ), (
        "mt5-gateway.spec nao empacota frontend/src-tauri/Python/models: "
        "o instalador vai sair sem os .pkl e o app instalado nao carrega modelo"
    )


def test_origem_dos_modelos_existe_e_tem_artefato():
    """A origem declarada precisa existir E conter `.pkl`/`.meta.json`.

    Um `datas.append` com caminho errado nao falha no build: o PyInstaller
    avisa e segue. O dano so aparece no app instalado. Aqui o erro aparece no
    CI, que e o lugar certo.
    """
    origem = RAIZ / "frontend" / "src-tauri" / "Python" / "models"
    assert origem.is_dir(), f"pasta de modelos ausente: {origem}"
    assert any(origem.glob("*.pkl")), f"nenhum .pkl em {origem}"


def test_destino_bate_com_o_que_ai_inference_procura():
    """O destino no bundle precisa ser o caminho que o runtime resolve.

    `ai_inference._resolver_modelos()` testa candidatos e vence o primeiro que
    tem artefato. Se o `.spec` escrever em `Python/models` e o runtime procurar
    outro lugar, o modelo esta no disco e continua invisivel.
    """
    from backend.ai_inference import _resolver_modelos

    resolvido = _resolver_modelos()
    assert resolvido.name == "models", (
        "ai_inference resolveu para "
        f"{resolvido}, que nao termina em `models` — o .spec deposita o "
        "artefato em `Python/models` e o runtime procuraria outro lugar"
    )
    assert any(resolvido.glob("*.meta.json")) or any(resolvido.glob("*.pkl")), (
        f"ai_inference resolveu para {resolvido}, que nao tem nenhum artefato"
    )