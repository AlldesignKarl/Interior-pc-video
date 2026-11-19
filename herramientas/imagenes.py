# -*- coding: utf-8 -*-
"""Genera la imagen anotada y los planos verticales (9:16) de cada componente.

Uso:  python3 herramientas/imagenes.py
Salida: imagenes/pc-interior-anotado.jpg y imagenes/planos/*.jpg
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guion_data as g  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTO = os.path.join(RAIZ, "imagenes", "pc-interior-original.jpg")
ACENTO = (255, 214, 64)
F = "/usr/share/fonts/opentype/inter/"


def fnt(nombre, tam):
    return ImageFont.truetype(F + nombre, tam)


# (número, etiqueta corta, posición del marcador, posición del texto relativo al marcador)
MARCAS = [
    ("1", "Placa base", (330, 600), "der"),
    ("2", "Procesador (bajo la bomba)", (657, 470), "der"),
    ("3", "Refrigeración líquida", (1570, 760), "izq"),
    ("4", "RAM", (892, 320), "der"),
    ("5", "SSD (bajo el disipador)", (516, 808), "der"),
    ("6", "Tarjeta gráfica", (330, 1150), "der"),
    ("7", "Fuente (escondida)", (520, 1620), "der"),
    ("8", "24 pines", (1045, 560), "der"),
    ("8", "8 pines CPU", (368, 205), "der"),
    ("8", "16 pines GPU", (782, 1330), "der"),
    ("9", "Ventiladores", (900, 128), "der"),
]

LEYENDA = [
    ("1", "Placa base", "ASUS ROG Strix Z690-F Gaming WiFi"),
    ("2", "Procesador", "Intel Core i9-14900K · 24 núcleos / 32 hilos · hasta 6,0 GHz"),
    ("3", "Refrigeración líquida", "be quiet! Light Loop 360 mm (bomba + tubos + radiador)"),
    ("4", "Memoria RAM", "G.Skill Trident Z5 RGB · 64 GB (2×32) DDR5-6000 CL30"),
    ("5", "SSD", "Samsung 990 Pro 1 TB · NVMe PCIe 4.0 · ~7.450 MB/s"),
    ("6", "Tarjeta gráfica", "Gigabyte GeForce RTX 5070 Ti AERO OC · 16 GB GDDR7"),
    ("7", "Fuente de alimentación", "Bajo la cubierta inferior (no se ve) · recomendada ~850 W"),
    ("8", "Cables de corriente", "24 pines → placa · 2×8 pines → CPU · 16 pines (12V-2x6) → GPU"),
    ("9", "Ventiladores / caja", "Corsair QL120 RGB · caja Corsair iCUE 5000X RGB QL Edition"),
]


def anotada():
    foto = Image.open(FOTO).convert("RGBA")
    W = foto.width
    alto_leyenda = 120 + 74 * len(LEYENDA) + 110
    lienzo = Image.new("RGBA", (W, foto.height + alto_leyenda), (12, 13, 20, 255))
    lienzo.paste(foto, (0, 0))
    ov = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f_num, f_lab = fnt("Inter-Black.otf", 40), fnt("Inter-Bold.otf", 36)
    for num, lab, (x, y), lado in MARCAS:
        w = d.textlength(lab, font=f_lab)
        if lado == "der":
            caja = (x + 30, y - 30, x + 30 + w + 50, y + 30)
        else:
            caja = (x - 30 - w - 50, y - 30, x - 30, y + 30)
        d.rounded_rectangle(caja, radius=16, fill=(10, 12, 20, 215))
        d.text((caja[0] + 25 + (12 if lado == "der" else 0), y - 22), lab, font=f_lab, fill=(255, 255, 255, 255))
        d.ellipse((x - 36, y - 36, x + 36, y + 36), fill=ACENTO + (255,), outline=(10, 12, 20, 255), width=5)
        tw = d.textlength(num, font=f_num)
        d.text((x - tw / 2, y - 25), num, font=f_num, fill=(12, 12, 18, 255))
    y0 = foto.height + 60
    d.text((60, y0), "¿Qué lleva este PC por dentro?", font=fnt("Inter-Black.otf", 54), fill=(255, 255, 255, 255))
    f_t, f_s = fnt("Inter-Bold.otf", 36), fnt("Inter-SemiBold.otf", 34)
    for i, (num, tit, sub) in enumerate(LEYENDA):
        y = y0 + 100 + i * 74
        d.ellipse((60, y, 112, y + 52), fill=ACENTO + (255,))
        tw = d.textlength(num, font=fnt("Inter-Black.otf", 32))
        d.text((86 - tw / 2, y + 7), num, font=fnt("Inter-Black.otf", 32), fill=(12, 12, 18, 255))
        d.text((136, y + 5), tit, font=f_t, fill=(255, 255, 255, 255))
        d.text((610, y + 7), sub, font=f_s, fill=(205, 210, 225, 255))
    credito = "Foto: Jacek Halicki · CC BY-SA 4.0 · Wikimedia Commons (anotaciones añadidas)"
    d.text((60, lienzo.height - 52), credito, font=fnt("Inter-SemiBold.otf", 26), fill=(150, 155, 170, 255))
    lienzo.alpha_composite(ov)
    destino = os.path.join(RAIZ, "imagenes", "pc-interior-anotado.jpg")
    lienzo.convert("RGB").save(destino, quality=90)
    print("Creada:", destino)


def plano(foto, cam, destino):
    _, cx, cy, h = cam
    w = h * 9 / 16
    cx = min(max(cx, w / 2), 1920 - w / 2)
    cy = min(max(cy, h / 2), 1920 - h / 2)
    caja = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    foto.resize((1080, 1920), Image.LANCZOS, box=caja).save(destino, quality=92)


def planos():
    foto = Image.open(FOTO).convert("RGB")
    carpeta = os.path.join(RAIZ, "imagenes", "planos")
    os.makedirs(carpeta, exist_ok=True)
    nombres = {
        "placa": ["01-placa-base"],
        "cpu": ["02a-procesador", "02b-procesador-abierto"],
        "refrigeracion": ["03a-bomba", "03b-tubos", "03c-radiador"],
        "ram": ["04a-ram", "04b-ram-abierto"],
        "ssd": ["05-ssd"],
        "grafica": ["06a-grafica-izquierda", "06b-grafica-derecha", "06c-grafica-salidas",
                    "06d-grafica-centro"],
        "fuente": ["07a-fuente-abajo", "07b-cable-24-pines", "07c-cables-cpu", "07d-cable-16-pines"],
    }
    for seg in g.SEGMENTOS:
        for (ancla, cam), nombre in zip(seg["camaras"], nombres.get(seg["id"], [])):
            if cam[0] != "v":
                continue
            plano(foto, cam, os.path.join(carpeta, nombre + ".jpg"))
    print("Planos en:", carpeta, sorted(os.listdir(carpeta)))


if __name__ == "__main__":
    anotada()
    planos()
