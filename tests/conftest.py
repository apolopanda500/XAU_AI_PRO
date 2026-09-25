"""Fixtures compartilhadas (Tk residente) para os testes de UI.

Um ÚNICO root Tk por processo, criado no início da sessão e destruído ao
final, evita a re-inicialização do pacote ttk/Tcl que falha em instalações
de Tk com libs incompletas (`ttk/menubutton.tcl` ausente) quando múltiplos
`Tk()` são criados ao longo do processo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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