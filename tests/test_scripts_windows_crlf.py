"""Os scripts de shell do Windows precisam de CRLF, e o defeito e invisivel.

O QUE HOUVE
===========
`scripts/build_app.bat` foi editado por uma ferramenta que grava LF. O
arquivo passou a ter LF puro em disco, e o build quebrou:

    '"ROOT=...scripts\.."' nao e reconhecido como comando
    'O' nao e reconhecido como comando interno
    ERRO: Nao foi possivel sincronizar os modelos

O `cmd.exe` nao reconhece `\n` como separador de comandos. Cada linha do
arquivo inteiro vira um comando, e o script morre na primeira.

POR QUE NINGUEM VIU
===================
O `.gitattributes` declara `*.bat text eol=crlf`, entao:

- No indice o arquivo fica em LF (correto, e o que o git armazena)
- No GitHub o runner faz checkout em CRLF e o build funciona
- Na copia de trabalho de quem editou, fica em LF e o build quebra

`git status` mostra o arquivo como **modificado** mas `git diff` sai vazio:
para o git, LF e CRLF sao o mesmo conteudo depois da normalizacao. O
defeito so aparece quando alguem roda o build na mao.

Por isso o teste olha os BYTES do arquivo em disco, e nao o conteudo.

O QUE ESTE TESTE FAZ
====================
Le `scripts/*.bat` e `scripts/*.ps1` da RAIZ DE TRABALHO e falha se algum
estiver com LF puro. No CI todos estarao em CRLF (o checkout normaliza), entao
o teste passa la — e e justamente por isso que ele precisa existir: ele
protege quem trabalha na copia de trabalho, que e onde o build quebra.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"

# Sufixos que o `cmd.exe`/PowerShell leem linha a linha e que exigem CRLF.
# `.sh` fica de fora de proposito: roda em Linux/macOS, onde LF e o certo.
EXTENSOES_CRITICAS = (".bat", ".cmd", ".ps1")


def _arquivos() -> list[Path]:
    achados: list[Path] = []
    for ext in EXTENSOES_CRITICAS:
        achados.extend(SCRIPTS.rglob(f"*{ext}"))
    return sorted(p for p in achados if p.is_file())


class TestScriptsWindowsUsamCRLF:
    @pytest.mark.parametrize(
        "arquivo", _arquivos(), ids=lambda p: p.name
    )
    def test_tem_crlf_e_nao_lf_puro(self, arquivo: Path):
        bruto = arquivo.read_bytes()
        if not bruto:
            pytest.skip(f"{arquivo.name} esta vazio")

        tem_crlf = b"\r\n" in bruto
        # CR solto (fora de CRLF) tambem e suspeito, mas so `\n` decide.
        total_lf = bruto.count(b"\n")

        assert tem_crlf or total_lf == 0, (
            f"{arquivo.relative_to(RAIZ)} esta com LF puro ({total_lf} linhas, "
            f"nenhum CRLF). O cmd.exe nao reconhece LF como separador: o script "
            f"vira N comandos invalidos e falha na primeira linha. O "
            f".gitattributes exige CRLF para *.{arquivo.suffix.lstrip('.')}; "
            f"converter: em PowerShell, ler o texto, trocar \\n por \\r\\n e "
            f"gravar em UTF-8 sem BOM."
        )

    def test_build_app_existe_e_esta_presente(self):
        """O build inteiro depende deste arquivo; se sumir, o ciclo morre."""
        alvo = SCRIPTS / "build_app.bat"
        assert alvo.is_file(), "scripts/build_app.bat sumiu do repositorio"
        assert alvo.stat().st_size > 0, "scripts/build_app.bat esta vazio"
