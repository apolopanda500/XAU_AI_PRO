"""
Design System PRO inspirado em TradingView + Binance + MetaTrader 5.
Cores escuras profissionais, glassmorphism, sombras e animações suaves.
"""
from __future__ import annotations


class MexcTheme:
    # === FUNDOS ===
    BG = "#0a0b0e"
    BG_SECONDARY = "#0d1117"
    PANEL = "#11141a"
    PANEL_HOVER = "#151923"
    CARD = "#161920"
    CARD_HOVER = "#1c212e"
    CARD_ALT = "#10151d"
    GLASS = "#1a1f2e"  # Glassmorphism base
    GLASS_HOVER = "#1f2538"

    # === BORDAS ===
    BORDER = "#1f232c"
    BORDER_LIGHT = "#2a2f3a"
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
    TEXT_SECONDARY = "#8b93a7"
    TEXT_MUTED = "#5c6477"
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
    SIDEBAR_WIDTH = 240
    HEADER_HEIGHT = 56
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
