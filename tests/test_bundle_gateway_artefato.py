# -*- coding: utf-8 -*-
"""O artefato tem o que o fonte pede — e nao so o que o `.spec` declara.

O PROBLEMA
==========
`tests/test_spec_gateway.py` trava que todo `backend/*.py` esta em
`hiddenimports` do `mt5-gateway.spec`. Isso e necessario e nao suficiente: o
`.spec` pode estar certo e o binario ter sido compilado ANTES da mudanca, ou o
empacotador ter ignorado a entrada.

Foi o que aconteceu em 05/10/2026 com `economic_calendar_publica`: o `.spec`
declara, o teste passa, e o executavel e de um build anterior. O app instalado
subiria normal e a rota responderia "agenda indisponivel" — sem excecao e sem
log.

POR QUE LER O ARTEFATO E TRABALHOSO
===================================
O `.exe` tem duas camadas. O CArchive tem 18 entradas, quase todas `pyi_rth_*`
do bootstrap — ler so ele daria "18 modulos" e pareceria que nada foi
empacotado. Os modulos Python estao no `PYZ.pyz`, que e um indice `marshal`
comprimido.

Tres detalhes medidos na leitura:

1. `ZlibArchiveReader(BytesIO(...))` quebra: `_parse_offset_from_filename`
   chama `rfind` no objeto recebido e `BytesIO` nao tem o metodo.
2. `CArchiveReader("caminho.exe?offset=N")` quebra com `OSError: [Errno 22]`:
   o Python trata `?` como caractere invalido em caminho no Windows.
3. **A posicao do `toc` NAO e o inicio do PYZ.** Medido: `toc` diz `132243` e a
   assinatura `PYZ\0` esta em `480915`. O que funciona e passar o deslocamento
   pelo parametro `start_offset` e achar a assinatura com `rfind`.

Este arquivo trava o ARTEFATO. O teste do `.spec` e o deste se complementam: um
declara a intencao, o outro prova o resultado.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "conferir_bundle_gateway.py"
EXECUTAVEL = RAIZ / "frontend" / "src-tauri" / "bridge" / "mt5-gateway.exe"


class TestScriptExiste:
    def test_o_script_esta_no_repo(self) -> None:
        # Sem isto, o `.spec` pode ser corrigido e o artefato continuar errado
        # sem ninguem notar: o script e a prova, e script nao versionado e
        # ausencia de prova.
        assert SCRIPT.exists(), f"conferidor ausente: {SCRIPT}"


class TestArtefatoQuandoExiste:
    """So roda quando o binario ja foi compilado.

    Nao e `xfail` nem `skip` disfarçado: em checkout limpo o binario nao existe
    porque e artefato de build, e o CI roda o checkout limpo. O que reprova e o
    BINARIO ERRADO, nao o binario ausente.
    """

    # `@classmethod` e obrigatorio: fixture de escopo de classe definida como
    # metodo de instancia e deprecada no pytest 10, e cada teste receberia uma
    # instancia nova — o `subprocess` rodaria uma vez por teste.
    @classmethod
    @pytest.fixture(scope="class")
    def resultado(cls) -> subprocess.CompletedProcess[str]:
        if not EXECUTAVEL.exists():
            pytest.skip(
                "gateway nao compilado neste checkout "
                "(o binario e artefato de build; rode scripts/build_app.bat)"
            )
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(RAIZ),
            timeout=300,
            check=False,
        )

    def test_o_conferidor_NAO_engole_erro(self, resultado) -> None:
        # Um conferidor que devolve saida vazia e codigo 0 nao prova nada.
        assert resultado.returncode in (0, 1), (
            f"o conferidor falhou ({resultado.returncode}): {resultado.stderr[-800:]}"
        )

    def test_todo_modulo_do_backend_esta_no_executavel(self, resultado) -> None:
        saida = resultado.stdout
        assert "modulos no bundle:" in saida, f"saida inesperada:\n{saida[-800:]}"
        assert "[XX ]" not in saida, (
            f"modulo ausente no bundle:\n{saida}\n"
            "  O app instalado sobe sem ele, sem erro visivel."
        )
        assert "REPROVADO" not in saida, saida

    def test_o_artefato_e_desta_sessao_e_nao_de_build_anterior(self) -> None:
        # O `.spec` pode ter sido corrigido depois do ultimo build. A
        # assinatura e o que prova que o binario travel junto.
        from backend import economic_calendar_publica

        if not EXECUTAVEL.exists():
            pytest.skip("gateway nao compilado neste checkout")
        fonte = EXECUTAVEL.stat().st_mtime
        codigo = Path(economic_calendar_publica.__file__).stat().st_mtime
        assert EXECUTAVEL.stat().st_mtime >= 0
        # O binario precisa ser MAIS NOVO que o modulo. Se for mais velho, o
        # `.spec` pode estar correto e o artefato ainda nao ter o codigo.
        assert fonte >= codigo - 2, (
            "o executavel e mais velho que backend/economic_calendar_publica.py: "
            f"exe={fonte:.0f}, fonte={codigo:.0f}. Refaca o build."
        )