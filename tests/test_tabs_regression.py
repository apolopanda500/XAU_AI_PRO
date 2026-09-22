"""Regressão: todas as abas do TopNav devem carregar sem erro.

Cobre o bug em que:
  - RobotTab chamava self.start_refresh_loop() inexistente;
  - _tab_factories não tinha as chaves "tools"/"integrations".

Sem rede e sem MT5. Os testes que instanciam o app usam um unico root Tk
por sessao (fixture `root_tk`) para evitar a re-inicializacao do pacote
Tcl/ttk em instalacoes de Tk com libs incompletas.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest


# Destinos que o TopNav expõe (app/components/topnav.py:TOP_ITEMS).
TOPNAV_KEYS = [
    "dashboard", "positions", "market", "charts", "robot",
    "audit", "tester", "vision", "settings", "connections",
]

ALIASES_HISTORICOS = ["tools", "integrations"]


# ---------------------------------------------------------------------------
# Estaticos: nao instanciam Tk, validam o contrato do codigo-fonte.
# ---------------------------------------------------------------------------

def _core_source() -> str:
    return (ROOT / "app" / "core.py").read_text(encoding="utf-8")


def test_tab_factories_declaram_todos_os_destinos():
    """Toda chave do TopNav e todo alias tem fabrica declarada em core.py."""
    src = _core_source()
    faltando = [k for k in TOPNAV_KEYS + ALIASES_HISTORICOS
                if f'"{k}": lambda' not in src]
    assert not faltando, f"fabricas ausentes em _tab_factories: {faltando}"


def test_robot_tab_tem_start_refresh_loop():
    """RobotTab declara start_refresh_loop/stop_auto_refresh (regressão)."""
    tree = ast.parse((ROOT / "app" / "tabs" / "robot.py").read_text(encoding="utf-8"))
    robot = next(n for n in tree.body
                 if isinstance(n, ast.ClassDef) and n.name == "RobotTab")
    metodos = {n.name for n in robot.body if isinstance(n, ast.FunctionDef)}
    assert "start_refresh_loop" in metodos, "start_refresh_loop ausente"
    assert "stop_auto_refresh" in metodos, "stop_auto_refresh ausente"


def test_robot_init_chama_metodo_existente():
    """O __init__ do RobotTab só pode chamar metodos definidos na classe."""
    tree = ast.parse((ROOT / "app" / "tabs" / "robot.py").read_text(encoding="utf-8"))
    robot = next(n for n in tree.body
                 if isinstance(n, ast.ClassDef) and n.name == "RobotTab")
    metodos = {n.name for n in robot.body if isinstance(n, ast.FunctionDef)}
    init = next(n for n in robot.body
                if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    chamadas_self = {
        node.func.attr
        for node in ast.walk(init)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    }
    definidos_ou_componentes = metodos | {
        "_build", "check_ea", "start_refresh_loop",
        "connect", "disconnect", "pack", "configure",
    }
    faltando = chamadas_self - definidos_ou_componentes
    assert not faltando, f"__init__ chama metodos inexistentes: {faltando}"


def test_imports_de_aba_estao_declarados_no_core():
    """Todos os destinos do TopNav têm import correspondente em core.py."""
    src = _core_source()
    for simbolo in ("DashboardTab", "PositionsTab", "TradingViewMarket",
                    "ChartsTab", "RobotTab", "ToolsTab", "StrategyTester",
                    "RobotVision", "SettingsTab", "IntegrationsTab"):
        assert f"import {simbolo}" in src, f"import {simbolo} ausente em core.py"


# ---------------------------------------------------------------------------
# Dinamico: instancia o app com o root Tk compartilhado da sessao.
# ---------------------------------------------------------------------------

@pytest.fixture()
def app(root_tk, monkeypatch):
    """Instancia o app e reaproveita o root Tk da sessao de testes."""
    # O XAUAProApp cria seu proprio tk.Tk(); apontamos para o root da
    # sessao para nao reinicializar o pacote Tcl/ttk (instalacoes de Tk
    # com libs incompletas falham em multiplos Tk()).
    import tkinter as tk
    monkeypatch.setattr(tk, "Tk", lambda *a, **k: root_tk)
    from app.core import XAUAProApp
    instance = XAUAProApp()
    yield instance
    for tab in instance.tabs.values():
        stopper = getattr(tab, "stop_auto_refresh", None)
        if callable(stopper):
            try:
                stopper()
            except Exception:
                pass


def test_todas_as_abas_carregam_sem_excecao(app):
    """Constroi cada aba de forma sincrona; qualquer erro falha o teste."""
    erros: list[str] = []
    for key in TOPNAV_KEYS:
        try:
            app._load_and_navigate(key)
        except Exception as exc:  # noqa: BLE001
            erros.append(f"{key}: {exc}")
            continue
        if key not in app.tabs:
            erros.append(f"{key}: aba nao registrada em app.tabs")
    assert not erros, "abas com falha de carregamento: " + "; ".join(erros)


def test_abas_registradas_tem_frame(app):
    """Cada aba instanciada expoe .frame (contrato do container de abas)."""
    for key in ("dashboard", "settings", "robot", "tools", "integrations"):
        app._load_and_navigate(key)
        tab = app.tabs.get(key)
        assert tab is not None, f"{key} nao carregada"
        assert hasattr(tab, "frame"), f"{key} sem atributo frame"

