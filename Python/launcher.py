# -*- coding: utf-8 -*-
"""XAU_AI_PRO Launcher (entry point do executavel PyInstaller).

Estrategia de empacotamento:
- O .exe (onefile) carrega as bibliotecas (pandas, sklearn, xgboost, ...).
- Os modulos do PROJETO (.py) sao importados do DISCO (pasta do projeto),
  para que Path(__file__).resolve().parent continue apontando para a pasta
  real (models/, datasets/, MQL5/Files/Data, .env) e nada quebre.

Uso:
    XAU_AI_PRO.exe                 -> menu interativo
    XAU_AI_PRO.exe predict         -> executa predicao
    XAU_AI_PRO.exe train           -> treina modelos
    XAU_AI_PRO.exe help            -> ajuda
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_MODULES = (
    "main",
    "predict",
    "train",
    "pipeline",
    "sentry_config",
    "model_registry",
    "mt5_bridge",
    "auto_retrain",
    "prediction_gateway",
    "financial_reconciliation",
    "event_sentry_bridge",
    "dashboard",
    "dashboard.app",
)


def _resolve_project_root() -> Path:
    """Em frozen: usa XAU_AI_PRO_ROOT ou CWD. Em dev: pasta pai de Python/."""
    if getattr(sys, "frozen", False):
        root = os.getenv("XAU_AI_PRO_ROOT")
        if root:
            return Path(root)
        return Path.cwd()
    return Path(__file__).resolve().parent.parent


def _load_env(root: Path) -> None:
    """Carrega o .env do disco para o ambiente (antes de importar sentry_config).

    No executable o __file__ aponta para o temp do PyInstaller; sem isso o
    SENTRY_DSN/ENVIRONMENT do disco seriam ignorados.
    """
    env_file = root / ".env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    except Exception:
        pass


def _bootstrap() -> Path:
    """Garante que os modulos do projeto venham do disco (nao do bundle)."""
    root = _resolve_project_root()
    py_dir = root / "Python"
    if py_dir.is_dir():
        # remove modulos do projeto eventualmente embutidos para importar do disco
        for mod in list(sys.modules):
            if mod in PROJECT_MODULES or mod.startswith("dashboard"):
                sys.modules.pop(mod, None)
        if str(py_dir) not in sys.path:
            sys.path.insert(0, str(py_dir))
    return root


def _menu() -> None:
    print()
    print("=" * 46)
    print("  XAU_AI_PRO - Robo de Trading XAU (Ouro)")
    print("=" * 46)
    print("  1) Executar PREDICAO (predict)")
    print("  2) Treinar MODELOS (train)")
    print("  3) Ajuda (help)")
    print("  0) Sair")
    print("-" * 46)
    choice = input("  Escolha uma opcao: ").strip()
    print()
    if choice == "1":
        _run("predict")
    elif choice == "2":
        _run("train")
    elif choice == "3":
        _run("help")
    elif choice == "0":
        print("  Encerrando. Ate mais!")
        sys.exit(0)
    else:
        print("  Opcao invalida.")
        _menu()


def _run(cmd: str) -> None:
    """Executa um comando do app (predict/train/help)."""
    sys.argv = [sys.argv[0], cmd]
    import main  # noqa: E402  (importado do disco pelo bootstrap)

    main.main()


def main() -> None:
    root = _bootstrap()
    os.environ.setdefault("XAU_AI_PRO_ROOT", str(root))
    _load_env(root)  # carrega .env (SENTRY_DSN/ENVIRONMENT) antes do import
    # define ENVIRONMENT para o Sentry (production se nao informado)
    os.environ.setdefault("ENVIRONMENT", "production")

    args = [a.lower() for a in sys.argv[1:]]
    if not args:
        _menu()
        return

    cmd = args[0]
    if cmd in ("predict", "train", "help"):
        _run(cmd)
    else:
        print(f"Comando desconhecido: {cmd}")
        print("Uso: XAU_AI_PRO.exe [predict|train|help]")
        sys.exit(1)


if __name__ == "__main__":
    main()