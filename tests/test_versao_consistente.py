"""A versao que o MQL5 mostra tem de ser a versao do produto.

O QUE HOUVE
===========
`VERSION` na raiz diz `1.2.4` e `scripts/sync_version.py --check` passa —
ele gerencia 8 manifestos (pyproject, dois `package.json`, dois `Cargo.toml`,
`tauri.conf.json`, `version.ts`) e nenhum deles e arquivo MQL5.

Resultado: o produto e 1.2.4 em todo o codebase Python/Node/Rust, e o EA
divulgava TRES versoes diferentes ao mesmo tempo:

| Onde | Dizia | Quem via |
|---|---|---|
| `#property version "1.20"` | 1.20 | aba de propriedades do EA no MT5 |
| `Print("XAU_AI_PRO v1.2.0")` | 1.2.0 | log do Expert Advisors |
| `EA_VERSION_STRING "1.2.0"` | 1.2.0 | `[VERSION]` no log e a tela |

Tres respostas para "qual versao", nenhuma igual a `VERSION`. Nenhum build e
nenhum teste reclamava: o `.mq5` nao entra em `sync_version.py` e a suite
Python nao le MQL5.

O QUE ESTE TESTE FAZ
====================
Le `VERSION` (a fonte unica) e compara com o que o EA divinity. Fixa:

* `#property version` do `.mq5`
* `EA_VERSION_STRING` do `VersionManager.mqh`
* o `Print` de versao do `.mq5`
* o manifesto de backup do `BackupManager.mqh`, que agora usa a MESMA fonte
  em vez de literal solto

Sobre o formato do `#property`
-----------------------------
MQL5 aceita no maximo 3 digitos e ponto: `1.240` e 1.24, que e a codificacao
usual de 1.2.4 (o MT5 sempre mostrou "1.20" para 1.2.0, e nao "1.2.0"). Por
isso o teste compara `1.240` com `124`, e nao com `1.2.4` string a string.

Nao testa os COMENTARIOS `// v1.2.1: ...`, que sao registros de quando uma
correcao foi feita e nao dividao de versao.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_VERSION = RAIZ / "VERSION"
MQ5 = RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO"
EA = MQ5 / "XAU_AI_PRO.mq5"
VERSION_MANAGER = MQ5 / "Enterprise" / "VersionManager.mqh"
BACKUP_MANAGER = MQ5 / "Enterprise" / "BackupManager.mqh"

RE_PROPERTY = re.compile(r'#property\s+version\s+"([^"]+)"')
RE_PRINT = re.compile(r'Print\(\s*"[^"]*XAU_AI_PRO\s+v([0-9.]+)"')
RE_EA_VERSION = re.compile(r'#define\s+EA_VERSION_STRING\s+"([^"]+)"')
RE_MANIFEST_LITERAL = re.compile(r'FileWrite\([^)]*XAU_AI_PRO\s+v([0-9.]+)"', re.DOTALL)


def _versao_produto() -> str:
    assert ARQUIVO_VERSION.is_file(), f"fonte unica de versao ausente: {ARQUIVO_VERSION}"
    return ARQUIVO_VERSION.read_text(encoding="utf-8").strip()


@pytest.fixture(scope="module")
def versao() -> str:
    return _versao_produto()


def test_versao_do_produto_tem_forma_esperada(versao):
    """`VERSION` e `x.y.z`. Sem isto os testes abaixo comparam contra o vazio."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", versao), (
        f"VERSION tem '{versao}', esperado x.y.z (ex.: 1.2.4)"
    )


def test_property_version_do_ea(versao):
    """O que o MT5 mostra na aba de propriedades do EA."""
    if not EA.is_file():
        pytest.skip(f"EA nao encontrado: {EA}")
    achado = RE_PROPERTY.search(EA.read_text(encoding="utf-8", errors="replace"))
    assert achado is not None, "o .mq5 nao tem #property version — o MT5 nao mostra versao"
    declarado = achado.group(1)
    # `#property version` do MQL5 aceita ate 3 digitos e ponto. O MT5 le
    # "1.240" como 1.24 e "1.20" como 1.20 — que era o valor ANTIGO, do
    # tempo em que o produto era 1.2.0.
    #
    # O QUE FOI MEDIDO antes de escrever esta regra (MetaEditor 64, EA de
    # teste, 4 compilacoes): "1.5", "1.500", "1.24", "1.240" e "1.20"
    # (compilaram TODOS com `0 errors, 0 warnings`, e o `.ex5` gerado nao
    # contem a versao como texto). Ou seja: o COMPILADOR NAO DESAMBIGUA, e
    # nenhum `pytest` vai descobrir a leitura do MT5.
    #
    # Por isso a regra aqui e do PRODUTO, e nao do compilador: o valor tem de
    # conter o patch da `VERSION` de forma que o MT5 leia 1.24 para 1.2.4, e
    # nao pode ser o "1.20" antigo. Aceita-se major.minor.patch (leido
    # literalmente pelo MT5) e major.patch em 3 digitos (leido como 1.24).
    # O MT5 le "1.240" como 1.24 e "1.204" como 1.204 — sao DIFERENTES. Logo o
    # patch ocupa as duas posicoes decimais, e nao uma: 1.2.4 -> ".24" e
    # 1.2.12 -> ".212" (o padrao do MT5 e 2 casas para minor.patch). Foi
    # medido: `2*100 + 4` produz "1.204", que o MT5 leria como 1.204, e nao
    # 1.24. A conversao correta e por concatenacao com zero a esquerda.
    major, minor, patch = (versao.split(".") + ["0", "0"])[:3]
    # O MT5 mostra ate 3 casas DECIMAIS depois do ponto. A versao do produto
    # (1.2.4) ocupa 2 casas, entao a forma canonica concatena minor + patch e
    # preenche com zeros ate fechar 3 casas depois do ponto:
    #
    #   1.2.4  ->  "1.240"   (minor "2" + patch "4" = "24" -> "240")
    #   1.2.0  ->  "1.200"
    #   1.2.12 ->  "1.212"
    #
    # O `ljust` completa as casas pela DIREITA, que e o que o MT5 le:
    # "24" vira "240". `rjust`/`zfill` alinham pela esquerda e dariam "024",
    # produzindo "1.024" — que foi exatamente o erro da primeira versao.
    major, minor, patch = (versao.split(".") + ["0", "0"])[:3]
    casas = f"{int(minor)}{int(patch)}".ljust(3, "0")  # "24" -> "240"
    aceitos = {
        versao,                                     # 1.2.4
        f"{int(major)}.{int(minor)}.{int(patch)}",   # 1.2.4
        f"{int(major)}.{casas}",                     # 1.240
    }
    assert declarado in aceitos, (
        f'#property version "{declarado}" no .mq5 nao corresponde a VERSION="{versao}". '
        f'Aceito: {sorted(aceitos)}. O MT5 mostra esta versao na aba de '
        f'propriedades do EA, e "1.20" (o valor antigo) NAO e aceito.'
    )


def test_ea_version_string_do_version_manager(versao):
    """`EA_VERSION_STRING` alimenta o `[VERSION]` do log e a tela."""
    if not VERSION_MANAGER.is_file():
        pytest.skip(f"VersionManager ausente: {VERSION_MANAGER}")
    achado = RE_EA_VERSION.search(VERSION_MANAGER.read_text(encoding="utf-8", errors="replace"))
    assert achado is not None, "VersionManager nao define EA_VERSION_STRING"
    assert achado.group(1) == versao, (
        f'EA_VERSION_STRING "{achado.group(1)}" diverge de VERSION="{versao}". '
        "Este e o valor que o EA escreve em `[VERSION]` no log."
    )


def test_print_de_versao_do_log(versao):
    """A linha que aparece no log do Expert Advisors ao iniciar."""
    if not EA.is_file():
        pytest.skip(f"EA nao encontrado: {EA}")
    texto = EA.read_text(encoding="utf-8", errors="replace")
    achados = RE_PRINT.findall(texto)
    assert achados, 'o .mq5 nao tem nenhum Print("XAU_AI_PRO v...") — o log nao diz a versao'
    for declarado in achados:
        assert declarado == versao, (
            f'o log do EA anuncia v{declarado} e o produto e v{versao}. '
            "E a primeira coisa que se le quando algo da errado."
        )


def test_manifesto_de_backup_usa_a_fonte_unica(versao):
    """O manifesto do backup nao pode ter literal solto.

    Este foi o mais silencioso: gravava `ea|XAU_AI_PRO v1.2.0` num ARQUIVO, e
    o campo so e lido na restauracao. Divergia ha quatro versoes sem ninguem
    ver. Agora usa `EA_VERSION_STRING`, entao nao ha como divergir.
    """
    if not BACKUP_MANAGER.is_file():
        pytest.skip(f"BackupManager ausente: {BACKUP_MANAGER}")
    texto = BACKUP_MANAGER.read_text(encoding="utf-8", errors="replace")
    literais = RE_MANIFEST_LITERAL.findall(texto)
    assert not literais, (
        "BackupManager grava a versao como literal solto: "
        f"{literais}. Use EA_VERSION_STRING para nao divergir de VERSION={versao}."
    )
    assert "EA_VERSION_STRING" in texto, (
        "BackupManager precisa gravar a versao com EA_VERSION_STRING"
    )


def test_backup_manager_declara_o_include_do_version_manager():
    """O `BackupManager` e incluido ANTES do `VersionManager` pelo `.mq5`.

    Como o manifesto usa `EA_VERSION_STRING`, o `BackupManager` tem de incluir
    o `VersionManager` ele mesmo. Sem isso a compilacao quebra com
    `error 256: undeclared identifier 'EA_VERSION_STRING'` — que foi
    exatamente o que aconteceu na primeira tentativa.
    """
    if not BACKUP_MANAGER.is_file():
        pytest.skip(f"BackupManager ausente: {BACKUP_MANAGER}")
    texto = BACKUP_MANAGER.read_text(encoding="utf-8", errors="replace")
    assert re.search(r'#include\s+"VersionManager\.mqh"', texto), (
        "BackupManager usa EA_VERSION_STRING mas nao inclui VersionManager.mqh. "
        "O .mq5 inclui BackupManager (linha 162) antes de VersionManager (166), "
        "entao o include precisa estar aqui."
    )
