"""Fixtures compartilhadas (Tk residente) para os testes de UI.

Um ÚNICO root Tk por processo, criado no início da sessão e destruído ao
final, evita a re-inicialização do pacote ttk/Tcl que falha em instalações
de Tk com libs incompletas (`ttk/menubutton.tcl` ausente) quando múltiplos
`Tk()` são criados ao longo do processo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Token usado pelos testes HTTP do gateway. Fica num lugar único para que os
#: arquivos de teste não repitam a string.
#:
#: NÃO é applied por fixture autouse de propósito. `fastapi_gateway` copia
#: `API_TOKEN = gw.API_TOKEN` no import; deixar o token setado desde o início da
#: sessão ativava o middleware de auth do FastAPI e `test_rejection_matrix`
#: passava a receber 401 onde esperava 403. Cada arquivo de teste do gateway
#: HTTP define o token na sua própria fixture.
TOKEN_DE_TESTE = "token-de-teste"

# `RATE_LIMIT_MAX`/`RATE_LIMIT_CMD_MAX` são lidos no IMPORT do módulo e são
# estado de processo. Um arquivo de teste que fazia reload com
# XAU_RATE_LIMIT=2 deixava a cota valendo e os testes seguintes levavam 429 sem
# relação com o que testavam. O padrão da sessão é sem limite; quem precisa de
# cota define na própria fixture.
os.environ.setdefault("XAU_RATE_LIMIT", "0")
os.environ.setdefault("XAU_RATE_LIMIT_CMD", "0")


@pytest.fixture(scope="session")
def root_tk():
    """Um único root Tk para toda a sessão de testes (headless)."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _sem_gateway_orfao():
    """Rede de segurança: nenhum subprocesso do gateway sobrevive à sessão.

    `XAUAProApp._start_threads()` sobe `backend/mt5_gateway.py` numa thread
    daemon. O processo filho é independente do pytest: se a suíte terminar
    sem encerrá-lo, ele continua segurando a porta 9001 e o app falha ao
    fazer bind no smoke test seguinte. Este autouse garante a limpeza mesmo
    se um teste futuro instanciar o app sem usar o fixture `app`.
    """
    yield
    try:
        from app.mt5_gateway import stop_gateway
        stop_gateway()
    except Exception:
        pass