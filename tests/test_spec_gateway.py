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


def test_modulos_do_calendario_estao_declarados():
    """Trava especifica: o calendario deste ciclo (05/10/2026).

    `economic_calendar_publica` e `planos.economic_calendar` sao importados
    DENTRO de `_economic_calendar`, e o PyInstaller so enxerga import de topo.
    Sem esta declaracao o gateway congelado sobe normal e a rota
    `/api/economic/calendar` responde "agenda indisponivel" — sem excecao e sem
    log. E o mesmo modo de falha do VIP, que por isso ganhou trava propria.
    """
    declarados = _hidden_imports_do_spec()
    for modulo in ("backend.economic_calendar_publica", "backend.planos.economic_calendar"):
        assert modulo in declarados, (
            f"{modulo} ausente do hiddenimports. O app instalado sobe sem o calendario."
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


def _pasta_de_modelos() -> Path:
    """Onde `train_multi.MODELOS_DIR` publica os `.pkl`.

    O mesmo caminho que o `.spec` empacota. Um `.pkl` e artefato de treino: nao
    vai no git (`.gitignore`, `**/Python/models/*.pkl`), e por isso a pasta
    some num checkout limpo. O CI roda o checkout limpo.
    """
    return RAIZ / "frontend" / "src-tauri" / "Python" / "models"


def _tem_artefato(pasta: Path) -> bool:
    return any(pasta.glob("*.pkl")) or any(pasta.glob("*.meta.json"))


#: Motivo unico do `skip`. Os tres testes de modelo abaixo medem o ARTEFATO
#: FINAL — `.pkl` e `.meta.json` sao resultado de treino e nao vao no git
#: (`.gitignore:49`). Num checkout limpo (CI, `git clone` novo) a pasta nao
#: existe e os tres medem zero artefato, reprovando sem que exista defeito.
#:
#: Isto NAO e o teste que "passava na maquina e falhou no CI" pela terceira
#: vez — e o oposto: o teste e sobre conteudo que o repositorio por decisao
#: NAO versiona. O padrao de `skip` ja existe no projeto e e o mesmo
#: (`tests/test_governanca_multi.py:39`, `tests/test_ai_inference.py:71`).
#:
#: O que continua valendo em qualquer checkout sao os testes de `hiddenimports`
#: e de `datas`, que leem o `.spec` e o fonte — e sao eles que pegam o defeito
#: real deste arquivo (modulo novo fora do bundle).
SKIP_SEM_ARTEFATO = (
    "sem catalogo de modelos neste checkout: os .pkl e .meta.json sao "
    "artefatos de treino e nao vao no git (.gitignore:49). Rode "
    "Python/ai/train_multi.py na maquina de operacao; no CI o que se verifica "
    "e o .spec (datas + hiddenimports), coberto pelos testes acima."
)


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
    origem = _pasta_de_modelos()
    if not _tem_artefato(origem):
        pytest.skip(SKIP_SEM_ARTEFATO)
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
    if not _tem_artefato(resolvido):
        # `resolvido.name == "models"` acima ja travou o defeito real (destino
        # do .spec diferente do caminho do runtime) e roda em qualquer checkout.
        # O que falta aqui e so a prova de que o artefato existe, e o
        # artefato nao e versionado.
        pytest.skip(SKIP_SEM_ARTEFATO)
    assert any(resolvido.glob("*.meta.json")) or any(resolvido.glob("*.pkl")), (
        f"ai_inference resolveu para {resolvido}, que nao tem nenhum artefato"
    )


def test_bundle_pyinstaller_tem_os_modelos():
    """O artefato final, medido — nao o codigo que o produz.

    Verificado em 02/10/2026: o `datas.append` estava certo, mas este teste
    procurava em `dist/mt5-gateway/Python/models`. O PyInstaller deposita
    `datas` em `_internal/`, entao a busca devolvia zero e o instalador saia
    sem os 3 modelos MULTI sem nenhum aviso no log.

    E por isso que a regra do ciclo e: medir o artefato, nao o codigo.
    """
    bundle = RAIZ / "dist" / "mt5-gateway"
    if not bundle.is_dir():
        pytest.skip("bundle ainda nao construido ( rode scripts/build_app.bat )")

    # PyInstaller coloca `datas` em `_internal/`. Aceita os dois para o teste
    # nao depender do layout interno.
    candidatos = [bundle / "Python" / "models", bundle / "_internal" / "Python" / "models"]
    com_modelos = [c for c in candidatos if c.is_dir() and any(c.glob("MULTI_*.pkl"))]
    assert com_modelos, (
        "o bundle nao tem nenhum MULTI_*.pkl em "
        + " nem ".join(str(c.relative_to(RAIZ)) for c in candidatos)
        + " — o instalador vai sair sem os modelos e o app instalado mostrara "
        "'modelos nao carregam', sem excecao em lugar nenhum"
    )


# ---------------------------------------------------------------------------
# O BUILD NAO PODE APAGAR OS MODELOS QUE ELE MESMO EMPACOTA
# ---------------------------------------------------------------------------
# Defeito medido em 03/10/2026. `scripts/build_app.bat`, passo [6/7], rodava
#
#     robocopy "Python\models" "frontend\src-tauri\Python\models" /MIR ...
#
# `/MIR` ESPELHA: apaga no destino tudo que nao esta na origem. A origem
# (`Python\models`, na raiz) tem 72 arquivos e ZERO `MULTI_*`, enquanto os tres
# modelos MULTI sao publicados por `train_multi.MODELOS_DIR` em
# `frontend\src-tauri\Python\models` — o proprio DESTINO do comando. Ou seja:
# todo build apagava da pasta que o `.spec` empacota exatamente os 3 modelos
# que o instalador precisa.
#
# Por que os testes deste arquivo nao pegaram: eles medem o `.spec` e o
# artefato JA CONSTRUIDO. O `/MIR` roda entre os dois — no meio do build — e o
# build passava limpo, sem excecao e sem log. E o defeito 7.2 de
# `Docs\SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md`, que perdeu 3 builds.
#
# Estes testes leem o `build_app.bat` como texto, entao valem em qualquer
# checkout e nao dependem de ter executado o build.

BUILD = RAIZ / "scripts" / "build_app.bat"


def _linhas_do_build() -> list[str]:
    assert BUILD.exists(), f"build_app.bat ausente: {BUILD}"
    return BUILD.read_text(encoding="utf-8", errors="replace").splitlines()


def _comando_dos_modelos() -> str:
    """A linha `robocopy` que sincroniza a pasta de modelos do Tauri.

    Localizada pelo par de pastas, e nao por numero de linha: a linha muda a
    cada build que acrescenta um passo, e um teste que quebra por renumeracao
    vira um teste que ninguem corrige.
    """
    for linha in _linhas_do_build():
        if "robocopy" in linha.lower() and "Python\\models" in linha and "/XD" in linha:
            return linha
    raise AssertionError(
        "build_app.bat nao tem mais a linha robocopy que sincroniza "
        "Python\\models -> frontend\\src-tauri\\Python\\models. Se o passo foi "
        "renomeado ou removido, confirme que o build ainda entrega os modelos "
        f"antes de remover este teste. Arquivo: {BUILD}"
    )


def test_build_nao_espelha_a_pasta_de_modelos():
    """O `/MIR` e o que apaga os MULTI. `/E` e o que nao apaga.

    Sem este teste a correcao de 03/10/2026 pode voltar a ser "simplificada"
    para `/MIR` por alguem que leia o comando como "sincronizar" e nao como
    "espelhar".
    """
    comando = _comando_dos_modelos()
    assert "/MIR" not in comando.upper(), (
        "build_app.bat usa `/MIR` para levar Python\\models a "
        "frontend\\src-tauri\\Python\\models. `/MIR` apaga no destino tudo que "
        "nao esta na origem, e a origem NAO tem os 3 modelos MULTI — sao "
        "publicados no proprio destino por train_multi.MODELOS_DIR. O build "
        "apaga da pasta que o .spec empacota os modelos que o instalador "
        "precisa, e passa limpo. Use `/E`. Comando:\n  " + comando
    )


def test_build_tem_trava_de_artefato_para_os_multi():
    """O build precisa FALHAR quando os MULTI nao estao no destino.

    O `/E` resolve o espelhamento, mas nao impede o proximo problema: alguem
    limpar a pasta, ou o treino nunca ter rodado. Sem esta trava o build
    termina com codigo 0 e entrega instalador sem modelo — o sintoma que a
    secao 7.2 do ciclo de 02/10 descreve: some sem erro.
    """
    linhas = _linhas_do_build()
    corpo = "\n".join(linhas)
    for modelo in ("MULTI_CRYPTO", "MULTI_FIAT", "MULTI_METALS"):
        assert modelo in corpo, (
            f"build_app.bat nao verifica {modelo}. Sem a trava de artefato o "
            "build empacota um instalador sem os modelos MULTI e passa limpo."
        )
    assert "MODELOS_DESTINO" in corpo, (
        "build_app.bat nao tem a trava de artefato dos modelos MULTI "
        "(esperado: a variavel MODELOS_DESTINO com o destino do .spec)."
    )
    # A trava precisa existir DEPOIS do robocopy, senao mede o estado anterior
    # a sincronizacao e nunca acusa o artefato que o comando acabou de perder.
    i_robo = next(
        i for i, linha in enumerate(linhas)
        if "robocopy" in linha.lower() and "Python\\models" in linha and "/XD" in linha
    )
    i_trava = next(
        (i for i, linha in enumerate(linhas) if "MODELOS_DESTINO" in linha), None
    )
    assert i_trava is not None and i_trava > i_robo, (
        "a trava dos modelos MULTI precisa ficar DEPOIS do robocopy: antes dela "
        "o build mede a pasta antes de sincronizar e nao acusa a perda."
    )


def test_origem_sem_multi_e_o_estado_que_torna_mir_destrutivo():
    """A assimetria que torna `/MIR` destrutivo esta medida, nao presumida.

    Este e o teste que fecha o ciclo: os dois acima leem o script, e um script
    pode estar correto enquanto o disco esta errado. Aqui mede-se a pasta de
    origem (`Python/models`, raiz) contra a de destino, que e a que
    `train_multi.MODELOS_DIR` publica e o `.spec` empacota.
    """
    origem = RAIZ / "Python" / "models"
    destino = _pasta_de_modelos()

    # Em checkout limpo nenhum dos dois lados tem artefato: nao ha o que medir
    # e o defeito nao existe. Os `.pkl` nao vao no git (`.gitignore:49`).
    if not destino.is_dir():
        pytest.skip(SKIP_SEM_ARTEFATO)
    if not any(origem.glob("MULTI_*")):
        # Origem sem MULTI e o estado NORMAL deste repositorio: e o motivo de
        # `/MIR` ser destrutivo. O que nao pode e o destino tambem estar vazio
        # num checkout onde ja houve treino — e o que os 25 testes de
        # `test_governanca_multi.py` medem.
        return

    assert any(destino.glob("MULTI_*")), (
        "a origem tem MULTI_ mas o destino nao. O build espelha a origem para o "
        "destino, entao o proximo build apaga o que esta no destino. Ver "
        "test_build_nao_espelha_a_pasta_de_modelos."
    )