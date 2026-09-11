# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw

img = Image.new('RGBA', (256, 256), (10, 11, 14, 255))
d = ImageDraw.Draw(img)
d.ellipse([20, 20, 236, 236], outline=(0, 198, 251, 255), width=18)
points = [(128, 80), (178, 140), (148, 140), (148, 190), (108, 190), (108, 140), (78, 140)]
d.polygon(points, fill=(0, 198, 251, 255))
sizes = [16, 32, 48, 64, 128, 256]
imgs = [img.resize((s, s), Image.LANCZOS) for s in sizes]
imgs[0].save('app/assets/icon.ico', sizes=[(s, s) for s in sizes], format='ICO')
print('icon.ico criado')
