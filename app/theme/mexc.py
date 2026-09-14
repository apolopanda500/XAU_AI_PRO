# -*- coding: utf-8 -*-
"""
Design System PRO inspirado em TradingView + Binance + MetaTrader 5.
Cores escuras profissionais, glassmorphism, sombras e animações suaves.
"""
from __future__ import annotations

from collections.abc import Callable


class MexcTheme:
    # === FUNDOS ===
    BG = "#0a0b0e"
    BG_SECONDARY = "#0d1117"
    PANEL = "#101720"
    PANEL_HOVER = "#152130"
    CARD = "#151d28"
    CARD_HOVER = "#1a2635"
    CARD_ALT = "#0e1620"
    GLASS = "#1a1f2e"  # Glassmorphism base
    GLASS_HOVER = "#1f2538"

    # === BORDAS ===
    BORDER = "#243244"
    BORDER_LIGHT = "#34465d"
    BORDER_ACCENT = "#00c6fb"
    GRID = "#233043"
    DIVIDER = "#1a1f2e"

    # === CORES PRIMÁRIAS (Ciano/Profissional) ===
    PRIMARY = "#00c6fb"
    PRIMARY_DARK = "#0072ff"
    PRIMARY_HOVER = "#33d4ff"
    PRIMARY_GRADIENT = ("#00c6fb", "#0072ff")
    PRIMARY_GLOW = "#00c6fb33"  # Glow sutil

    # === DESTAQUE (Laranja/Alerta) ===
    ACCENT = "#ff8c00"
    ACCENT_HOVER = "#ffa733"
    ACCENT_GLOW = "#ff8c0033"

    # === ESTADOS ===
    SUCCESS = "#00c853"
    SUCCESS_DARK = "#0d7a3e"
    SUCCESS_GLOW = "#00c85333"
    DANGER = "#ff3d57"
    DANGER_DARK = "#b91c3c"
    DANGER_GLOW = "#ff3d5733"
    WARNING = "#ffb300"
    WARNING_DARK = "#c78a00"
    WARNING_GLOW = "#ffb30033"
    INFO = "#00c6fb"
    INFO_GLOW = "#00c6fb33"

    # === TEXTO ===
    TEXT = "#f0f2f5"
    TEXT_SECONDARY = "#9ca9bd"
    TEXT_MUTED = "#68778c"
    TEXT_SOFT = "#aab4c8"
    TEXT_DISABLED = "#3d4555"

    # === GRÁFICO (Cores de candlestick) ===
    CHART_UP = "#00c853"
    CHART_DOWN = "#ff3d57"
    CHART_UP_AREA = "#00c85320"  # Área preenchida verde
    CHART_DOWN_AREA = "#ff3d5720"  # Área preenchida vermelha
    CHART_GRID = "#1a1f2e"
    CHART_CROSSHAIR = "#2a2f3a"

    # === TERMINAL (Bid/Ask) ===
    BID = "#00c853"
    ASK = "#ff3d57"
    SPREAD = "#ffb300"

    # === FONTES ===
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"
    FONT_DIGITAL = "Courier New"

    # === DIMENSÕES ===
    SIDEBAR_WIDTH = 260
    HEADER_HEIGHT = 68
    FOOTER_HEIGHT = 32
    BORDER_RADIUS = 8

    # === ANIMAÇÃO ===
    GLOW = "#00c6fb"
    SHADOW = "#00000066"
    TRANSITION_FAST = 150
    TRANSITION_NORMAL = 300

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return {
            k: v
            for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        }


# Alias para importação mais curta
Theme = MexcTheme

_THEME_CALLBACKS: list[Callable[[], None]] = []


def on_theme_change(callback: Callable[[], None]) -> Callable[[], None]:
    """Registra callback para atualizar widgets após troca de tema."""
    if callback not in _THEME_CALLBACKS:
        _THEME_CALLBACKS.append(callback)

    def unsubscribe() -> None:
        try:
            _THEME_CALLBACKS.remove(callback)
        except ValueError:
            pass

    return unsubscribe

# ============================================================
# TEMAS MULTIPLOS (aplicados no boot antes de construir a UI)
# ============================================================
_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "BG": "#0a0b0e", "BG_SECONDARY": "#0d1117", "PANEL": "#101720",
        "PANEL_HOVER": "#152130", "CARD": "#151d28", "CARD_HOVER": "#1a2635",
        "CARD_ALT": "#0e1620", "BORDER": "#243244", "BORDER_LIGHT": "#34465d",
        "PRIMARY": "#00c6fb", "PRIMARY_HOVER": "#33d4ff", "ACCENT": "#ff8c00",
        "SUCCESS": "#00c853", "DANGER": "#ff3d57", "WARNING": "#ffb300",
        "TEXT": "#f0f2f5", "TEXT_SECONDARY": "#9ca9bd", "TEXT_MUTED": "#68778c",
    },
    "midnight": {
        "BG": "#070c1a", "BG_SECONDARY": "#0b1226", "PANEL": "#101a38",
        "PANEL_HOVER": "#16234a", "CARD": "#131f45", "CARD_HOVER": "#1a2b59",
        "CARD_ALT": "#0d1730", "BORDER": "#23325c", "BORDER_LIGHT": "#33467a",
        "PRIMARY": "#4d9fff", "PRIMARY_HOVER": "#74b4ff", "ACCENT": "#ffd700",
        "SUCCESS": "#2ecc71", "DANGER": "#ff5c7a", "WARNING": "#ffc53d",
        "TEXT": "#eef2ff", "TEXT_SECONDARY": "#93a4cc", "TEXT_MUTED": "#5a6b96",
    },
    "graphite": {
        "BG": "#0d0f12", "BG_SECONDARY": "#121418", "PANEL": "#171a1f",
        "PANEL_HOVER": "#1e2229", "CARD": "#1c2026", "CARD_HOVER": "#242a33",
        "CARD_ALT": "#14171c", "BORDER": "#2c323c", "BORDER_LIGHT": "#3d4550",
        "PRIMARY": "#e8c15a", "PRIMARY_HOVER": "#f2d47a", "ACCENT": "#ff8c00",
        "SUCCESS": "#7fd67f", "DANGER": "#ef6a6a", "WARNING": "#e8c15a",
        "TEXT": "#f2f2f0", "TEXT_SECONDARY": "#a2a8b0", "TEXT_MUTED": "#6b7078",
    # =========================================================================
    # XAU/USD — Ouro institucional: fundo dourado profundo, acentos em
    # amarelo-ouro vivo, textos em branco gelo. Estilo trading room real.
    # =========================================================================
    "xau_dark": {
        "BG": "#0c0a05", "BG_SECONDARY": "#12100a", "PANEL": "#18150e",
        "PANEL_HOVER": "#1f1b12", "CARD": "#221e14", "CARD_HOVER": "#2a2519",
        "CARD_ALT": "#0f0d08", "BORDER": "#3a3220", "BORDER_LIGHT": "#5a4f38",
        "PRIMARY": "#ffc94d", "PRIMARY_HOVER": "#ffe08a", "ACCENT": "#ff7300",
        "SUCCESS": "#4ade80", "DANGER": "#ff4d6a", "WARNING": "#ffb347",
        "TEXT": "#f5f0e8", "TEXT_SECONDARY": "#c2b89e", "TEXT_MUTED": "#7a7060",
    },
    # =========================================================================
    # BTC/USD — Cripto profissional: fundo azul-nocturno, acentos em
    # verde-neon (estilo Binance spot), textos em off-white.
    # =========================================================================
    "btc_dark": {
        "BG": "#070b0f", "BG_SECONDARY": "#0d1420", "PANEL": "#121c2e",
        "PANEL_HOVER": "#18263b", "CARD": "#162236", "CARD_HOVER": "#1d2c44",
        "CARD_ALT": "#0a1119", "BORDER": "#253553", "BORDER_LIGHT": "#3a4d6e",
        "PRIMARY": "#00e676", "PRIMARY_HOVER": "#69f0ae", "ACCENT": "#ffd740",
        "SUCCESS": "#00e676", "DANGER": "#ff5252", "WARNING": "#ffd740",
        "TEXT": "#eef4ff", "TEXT_SECONDARY": "#90a4c4", "TEXT_MUTED": "#54688d",
    },
    },
}


def apply_theme(name: str) -> None:
    """Aplica um tema: atualiza os atributos da classe MexcTheme in-place."""
    name = (name or "dark").strip().lower()
    palette = _THEMES.get(name)
    if palette is None:
        palette = _THEMES["dark"]
    for key, value in palette.items():
        setattr(Theme, key, value)
    for callback in tuple(_THEME_CALLBACKS):
        try:
            callback()
        except Exception:
            # Um widget destruido nao pode impedir a troca global de tema.
            try:
                _THEME_CALLBACKS.remove(callback)
            except ValueError:
                pass
