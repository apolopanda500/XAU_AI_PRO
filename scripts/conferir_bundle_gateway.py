"""Confere se um modulo esta DENTRO do executavel congelado.

POR QUE ISTO EXISTE
===================
Um modulo de `backend/` fora do `hiddenimports` do `.spec` simplesmente nao
existe dentro do `.exe`. O sintoma do usuario e "a tela nao mostra", sem excecao
e sem log nenhum: o app sobe normal.

Aconteceu duas vezes no mesmo projeto:
  - `metas_vip`, `acesso` e `vip_progress` ausentes na primeira instalacao, e a
    tela de VIP sem nada;
  - `economic_calendar_publica` e `planos.economic_calendar`, que sao importados
    DENTRO de `_economic_calendar` e por isso o PyInstaller nao ve.

`tests/test_spec_gateway.py` trava a declaracao no `.spec`. Este script trava o
artefato: o `.spec` pode estar certo e o build ter sido feito antes da mudanca,
ou o empacotador ter ignorado a entrada. O texto "carnes" esta no arquivo e o
que importa e se ele viaja no bundle.

COMO LÊ
=======
O `.exe` tem duas camadas: o CArchive (18 entradas, a maioria `pyi_rth_*` do
bootstrap) e o `PYZ.pyz`, que e onde os modulos Python ficam de verdade. Ler
so o CArchive daria "18 modulos" e pareceria que nada esta empacotado.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.loader import pyimod01_archive

RAIZ = Path(__file__).resolve().parent.parent


def modulos_do_pyz(executavel: Path) -> set[str]:
    """Nomes de modulo dentro do `PYZ.pyz` do executavel.

    Tres tentativas foram necessarias para ler isso, e as duas primeiras
    quebraram de jeitos que merecem registro:

    1. `ZlibArchiveReader(BytesIO(...))` — quebra em
       `_parse_offset_from_filename`, que chama `rfind` no objeto recebido e um
       `BytesIO` nao tem o metodo.
    2. `CArchiveReader("caminho.exe?offset=N")` — o PyInstaller 6.x le esse
       formato, mas a `open()` do Python trata `?` como caractere invalido no
       caminho e levanta `OSError: [Errno 22] Invalid argument`.

    O deslocamento NAO vem do `toc`. MEDIDO nesta sessao: o `toc` diz
    `132243` e a assinatura `PYZ\0` esta em `480915`. A razao e que a posicao do
    `toc` e o inicio do BLOCO como o empacotador o gravou, e nao o inicio do
    `PYZ.pyz` logico.

    Menos tentativas e mais honesto: procurar a assinatura no arquivo, como o
    proprio PyInstaller faz ao montar o bootloader. `rfind` (e nao `find`) porque
    um modulo empacotado pode conter os bytes `PYZ\0` no meio do conteudo, e a
    assinatura do PYZ e a ULTIMA delas.
    """
    carchive = CArchiveReader(str(executavel))
    if carchive.toc.get("PYZ.pyz") is None:
        raise LookupError(f"{executavel} nao tem PYZ.pyz: nao e um bundle PyInstaller")
    with open(executavel, "rb") as fp:
        bruto = fp.read()
    inicio = bruto.rfind(b"PYZ\x00")
    if inicio < 0:
        raise LookupError(f"{executavel}: assinatura PYZ nao encontrada")
    z = pyimod01_archive.ZlibArchiveReader(str(executavel), start_offset=inicio)
    return set(z.toc)


def conferir(executavel: Path, obrigatorios: list[str]) -> int:
    print(f"artefato: {executavel}")
    print(f"tamanho : {executavel.stat().st_size / 1024 / 1024:.1f} MB")
    presentes = modulos_do_pyz(executavel)
    print(f"modulos no bundle: {len(presentes)}")
    print()
    faltando: list[str] = []
    for modulo in obrigatorios:
        tem = any(modulo in nome for nome in presentes)
        print(f"  [{'ok' if tem else 'XX '}] {modulo}")
        if not tem:
            faltando.append(modulo)
    print()
    if faltando:
        print("REPROVADO: ausente no bundle -> " + ", ".join(faltando))
        print("  O app instalado vai subir sem isso, sem erro visivel.")
        print("  Confirme que o modulo esta em `hiddenimports` do .spec e REFAÇA o build.")
        return 1
    print("OK: todos os modulos exigidos estao dentro do executavel.")
    return 0


if __name__ == "__main__":
    destino = RAIZ / "frontend" / "src-tauri" / "bridge" / "mt5-gateway.exe"
    if not destino.exists():
        print(f"artefato ausente: {destino}")
        raise SystemExit(2)
    # Todo `backend/*.py` do fonte tem de viajar. E a lista completa, e nao uma
    # amostra: um modulo a menos aqui e um modulo a menos no app instalado.
    modulos = sorted(
        f"backend.{p.stem}"
        for p in (RAIZ / "backend").glob("*.py")
        if p.stem != "__init__"
    )
    modulos.append("backend.planos.economic_calendar")
    raise SystemExit(conferir(destino, modulos))