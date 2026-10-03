"""O EA precisa COMPILAR, e nada no repositorio cobra isso.

O QUE HOUVE
==========
`Core/ExecutionEngine.mqh:278` chamou `OrderSendResult()`:

    uint erroBroker = (uint)OrderSendResult();

Essa funcao NAO EXISTE em MQL5. Introduzida no commit `dbdce10` e nunca
compilada:

    error 256: undeclared identifier 'OrderSendResult'
    Result: 2 errors, 3 warnings

Ninguem viu por tres razoes que se somam:

1. **A suite Python nao compila MQL5.** Ela roda contra o fonte; `mq5`/`mqh`
   nao sao modulos.
2. **O `.ex5` nao e versionado** (`.gitignore:37`, `MQL5/Experts/*/*.ex5`), e
   nao havia nenhum no repositorio. O artefato que prova a compilacao e, por
   decisao, justamente o que nao existe.
3. **O build do repositorio tambem nao compila MQL5** (`AGENTS.md`). O CI
   inteiro e cego a isso.

Resultado: o EA estava quebrado e a tela toda verde — 833 testes Python
passando ao lado de um EA que nao compilava.

O QUE ESTE TESTE FAZ
====================
Compila de verdade com o `MetaEditor64` e reprova se sair qualquer erro.
E caro (medido: ~11 s) e externo ao repositorio, entao:

* pula quando o `MetaEditor64.exe` nao existe (Linux no CI, outra maquina);
* pula quando o `.mq5` nao esta no disco;
* **NUNCA e `xfail`**: onde o compilador existe e ha codigo, ele tem de
  passar. Um `skip` que mascarasse erro aqui seria o mesmo defeito que este
  arquivo denuncia.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EA = RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.mq5"

#: Candidatos de instalacao, do mais especifico ao generico. O primeiro
#: achado vence. `C:\Program Files\MetaTrader 5` e o padrao do MT5 no
#: Windows; as variantes cobrem `Program Files (x86)` e o `build` do
#: instalador portable.
CANDIDATOS_METAEDITOR = (
    Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\MetaEditor64.exe"),
    Path(r"C:\Program Files\MetaTrader 5\build\MetaEditor64.exe"),
)

#: `Result: N errors, M warnings, ...` e a ultima linha de quem NAO teve
#: erro de parse (quem falhou nao chega a esse ponto). Os dois numeros sao
#: lidos para que um aviso novo apareca no teste em vez de passar calado.
RE_RESULT = re.compile(r"Result:\s*(\d+)\s+errors?,\s*(\d+)\s+warnings?", re.IGNORECASE)
RE_ERROR = re.compile(r"^.*:\s*(error|warning)\s+\d+:", re.IGNORECASE)


def _metaeditor() -> Path | None:
    for caminho in CANDIDATOS_METAEDITOR:
        if caminho.is_file():
            return caminho
    achado = shutil.which("metaeditor64.exe")
    return Path(achado) if achado else None


def _compilar(exe: Path) -> tuple[int, str]:
    """Compila o EA e devolve `(codigo_de_saida, log)`."""
    with tempfile.TemporaryDirectory(prefix="xau_mql5_compile_") as tmp:
        log = Path(tmp) / "compile.log"
        concluida = subprocess.run(
            [str(exe), f"/compile:{EA}", f"/log:{log}"],
            capture_output=True,
            text=True,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        conteudo = ""
        if log.is_file():
            # O log e gravado em UTF-16 pelo MetaEditor; se vier vazio,
            # tenta-se UTF-8 antes de concluir que nao houve log.
            conteudo = log.read_text(encoding="utf-16", errors="replace")
            if not conteudo.strip():
                conteudo = log.read_text(encoding="utf-8", errors="replace")
        return concluida.returncode, conteudo


def test_ea_compila_sem_erro():
    """O EA compila com `0 errors`.

    Este e o teste que teria reprovado o commit `dbdce10` no proprio dia.
    """
    exe = _metaeditor()
    if exe is None:
        pytest.skip(
            "MetaEditor64.exe nao encontrado: este teste so roda na maquina de "
            "compilacao MQL5 (o CI em Linux nao tem MetaEditor)"
        )
    if not EA.is_file():
        pytest.skip(f"EA nao encontrado: {EA}")

    codigo, log = _compilar(exe)

    # As linhas de erro do compilador sao a fonte da verdade. A linha `Result`
    # e a confirmacao; as duas sao verificadas porque ja acontece de o log
    # vir truncado e ainda conter "Result: 0 errors".
    problemas = [ln for ln in log.splitlines() if RE_ERROR.search(ln)]
    erros = [ln for ln in problemas if "error" in ln.lower()]

    assert not erros, (
        "o EA NAO COMPILA. Erros do MetaEditor64:\n  "
        + "\n  ".join(erros[:25])
        + f"\n\n(codigo de saida {codigo}; log com {len(log)} chars)"
    )

    # `warning 63: cannot be used for static allocated array` e o aviso que
    # apareceu ao usar `ArrayResize` em array estatico: indica que o binario
    # gerado NAO corresponde ao fonte. Compilar limpo com esse aviso e o build
    # silenciosamente diferente do que se le no editor.
    w63 = [ln for ln in problemas if "warning 63" in ln.lower()]
    assert not w63, (
        "o EA compila mas com `warning 63` (ArrayResize em array estatico): "
        "o resultado NAO corresponde ao fonte.\n  " + "\n  ".join(w63[:15])
    )


def test_log_da_compilacao_e_interpretavel():
    """A linha `Result:` existe e diz zero erros.

    Sem este teste, um MetaEditor que falha em silencio (log vazio, ou nao
    gravado) passaria: `erros` seria uma lista vazia e o `assert` do teste
    acima ficaria verde sem nunca ter compilado nada.
    """
    exe = _metaeditor()
    if exe is None:
        pytest.skip("MetaEditor64.exe nao encontrado")
    if not EA.is_file():
        pytest.skip(f"EA nao encontrado: {EA}")

    _codigo, log = _compilar(exe)

    achado = RE_RESULT.search(log)
    assert achado is not None, (
        "o log da compilacao nao tem a linha `Result:`. Ou o MetaEditor "
        "falhou antes de compilar, ou mudou o formato do log — e nesse caso "
        "este teste mede NADA sem avisar.\n"
        f"log ({len(log)} chars):\n{log[:800]}"
    )
    n_err = int(achado.group(1))
    assert n_err == 0, f"a propria linha Result reporta {n_err} erro(s)"
    # Nao se fixa um teto de warnings aqui: escolher quais avisos importam e
    # discussao de estilo. O que nao pode e `errors != 0`.
    """Compila o EA e devolve `(codigo_de_saida, log)`."""
    with tempfile.TemporaryDirectory(prefix="xau_mql5_compile_") as tmp:
        log = Path(tmp) / "compile.log"
        concluida = subprocess.run(
            [str(exe), f"/compile:{EA}", f"/log:{log}"],
            capture_output=True,
            text=True,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        conteudo = ""
        if log.is_file():
            # O log e gravado em UTF-16 pelo MetaEditor; se vier vazio,
            # tenta-se UTF-8 antes de concluir que nao houve log.
            conteudo = log.read_text(encoding="utf-16", errors="replace")
            if not conteudo.strip():
                conteudo = log.read_text(encoding="utf-8", errors="replace")
        return concluida.returncode, conteudo