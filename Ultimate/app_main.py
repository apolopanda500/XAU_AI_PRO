"""
XAU AI PRO - Entry point da interface desktop.
Uso:
    python Ultimate/app_main.py

Abre a GUI (login + mercado em tempo real + treinamento + API).
No executavel (PyInstaller) abre direto nas abas com auto-login admin.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante os imports relativos ao Ultimate - funcione tanto no PyInstaller quanto direto
ULT = Path(__file__).resolve().parent
if str(ULT) not in sys.path:
    sys.path.insert(0, str(ULT))

# Define a pasta de dados persistentes FORA do _MEIPASS temporario
# (arquivos gerados pelo app - config, db - sao salvos na pasta do usuario)
try:
    _appdata = Path(os.environ.get("APPDATA", str(Path.home()))) / "XAU_AI_PRO"
    _appdata.mkdir(parents=True, exist_ok=True)
    os.environ["XAU_AI_PRO_DATA"] = str(_appdata)
    # Se estiver executando dentro de onefile, copia config.json padrao para appdata
    if getattr(sys, "frozen", False):
        import shutil
        _meipass = Path(getattr(sys, "_MEIPASS", Path(ULT)))
        _src = _meipass / "config.json"
        _dst = _appdata / "config.json"
        if _src.exists() and not _dst.exists():
            shutil.copy2(str(_src), str(_dst))
        os.environ["XAU_AI_PRO_CONFIG"] = str(_dst)
except Exception:
    pass

os.chdir(str(ULT))


def _res_main() -> None:
    """Importa todos os modulos locais explicitamente antes do main."""
    import config_store
    import market_live
    import mt5_integration
    import themes
    import wallpaper
    import assistant
    import daily_tools
    import integrations
    import design_system
    from gui import main as gui_main

    gui_main()


def main() -> None:
    try:
        _res_main()
    except Exception as e:
        # Mostra o erro em uma caixa de dialogo para debug
        import traceback
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("XAU AI PRO - Erro", f"Falha ao iniciar:\n{e}\n\n{traceback.format_exc()}")
        root.destroy()


if __name__ == "__main__":
    main()