"""
Design System inspirado na exchange MEXC.
Cores escuras profundas, acentos em ciano/laranja, cards elevados.
"""
from __future__ import annotations


class MexcTheme:
    # Fundos
    BG = "#0a0b0e"
    BG_SECONDARY = "#0d1117"
    PANEL = "#11141a"
    CARD = "#161920"
    CARD_HOVER = "#1c212e"

    # Bordas
    BORDER = "#1f232c"
    BORDER_LIGHT = "#2a2f3a"
    BORDER_ACCENT = "#00c6fb"

    # Primária (ciano/azul)
    PRIMARY = "#00c6fb"
    PRIMARY_DARK = "#0072ff"
    PRIMARY_HOVER = "#33d4ff"
    PRIMARY_GRADIENT = ("#00c6fb", "#0072ff")

    # Destaque (laranja)
    ACCENT = "#ff8c00"
    ACCENT_HOVER = "#ffa733"

    # Estados
    SUCCESS = "#00c853"
    SUCCESS_DARK = "#0d7a3e"
    DANGER = "#ff3d57"
    DANGER_DARK = "#b91c3c"
    WARNING = "#ffb300"
    WARNING_DARK = "#c78a00"
    INFO = "#00c6fb"

    # Texto
    TEXT = "#f0f2f5"
    TEXT_SECONDARY = "#8b93a7"
    TEXT_MUTED = "#5c6477"

    # Gráfico
    CHART_UP = "#00c853"
    CHART_DOWN = "#ff3d57"

    # Fontes
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return {
            k: v
            for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        }


# Alias para importação mais curta
Theme = MexcTheme
