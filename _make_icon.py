# -*- coding: utf-8 -*-
"""Gera icone do XAU_AI_PRO (ouro + candles) em .png e .ico."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# fundo: gradiente escuro (azul petroleo -> preto)
for y in range(SIZE):
    t = y / SIZE
    r = int(12 + 8 * t)
    g = int(22 + 10 * t)
    b = int(38 + 12 * t)
    d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

# circulo dourado (moeda)
cx, cy, rad = 128, 118, 86
d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(200, 160, 60, 255), outline=(255, 215, 90, 255), width=6)
# brilho interno
d.ellipse([cx - 66, cy - 66, cx + 66, cy + 66], outline=(255, 235, 160, 120), width=3)

# candles (verde subindo / vermelho descendo)
candles = [
    (70, 140, 170, "up"),      # x, topo, base
    (100, 90, 150, "up"),
    (130, 120, 165, "down"),
    (160, 80, 140, "up"),
    (190, 110, 150, "down"),
]
for x, top, base, kind in candles:
    w = 16
    body_top = min(top, base)
    body_bot = max(top, base)
    color = (60, 200, 110, 255) if kind == "up" else (230, 70, 70, 255)
    # pavio
    d.line([(x + w // 2, body_top - 8), (x + w // 2, body_bot + 8)], fill=color, width=3)
    # corpo
    d.rounded_rectangle([x, body_top, x + w, body_bot], radius=3, fill=color)

# linha de tendencia ascendente
d.line([(62, 178), (198, 82)], fill=(255, 215, 90, 255), width=5)

# texto "XAU" centralizado
try:
    font = ImageFont.truetype("arialbd.ttf", 30)
except Exception:
    font = ImageFont.load_default()
d.text((cx, 210), "XAU", font=font, fill=(255, 235, 180, 255), anchor="mm")

# borda externa
d.rounded_rectangle([2, 2, SIZE - 2, SIZE - 2], radius=28, outline=(255, 215, 90, 160), width=4)

# salvar
img.save("assets/icon.png")
# icone multi-resolucao
img.save("assets/icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("OK: assets/icon.png + assets/icon.ico")