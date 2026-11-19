# -*- coding: utf-8 -*-
"""Genera el vídeo borrador vertical (1080x1920) + subtítulos .srt a partir de guion_data.py.

Uso:  python3 herramientas/render_video.py
Salida: video/como-funciona-un-pc_borrador.mp4, video/subtitulos.srt, video/tiempos.json
Necesita: Pillow y ffmpeg.
"""
import json
import math
import os
import re
import subprocess
import sys
from multiprocessing import Pool

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guion_data import SEGMENTOS  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTO = os.path.join(RAIZ, "imagenes", "pc-interior-original.jpg")
SALIDA = os.path.join(RAIZ, "video")
W, H, FPS = 1080, 1920, 30
ACENTO = (255, 214, 64)
FUENTES = "/usr/share/fonts/opentype/inter/"
CREDITO = "Foto: Jacek Halicki · CC BY-SA 4.0 · Wikimedia Commons"
DUR_MOV = 0.75  # segundos que tarda la cámara en ir de un plano a otro


def fuente(peso, tam):
    nombre = {"black": "Inter-Black.otf", "bold": "Inter-Bold.otf",
              "semi": "Inter-SemiBold.otf", "xbold": "Inter-ExtraBold.otf"}[peso]
    return ImageFont.truetype(FUENTES + nombre, tam)


# ------------------------------------------------------------------ tiempos ---
def dur_palabra(p):
    limpia = re.sub(r"[¿?¡!.,:;…]", "", p)
    dig = sum(c.isdigit() for c in limpia)
    letras = sum(c.isalpha() for c in limpia)
    if dig:
        d = 0.18 + 0.15 * dig + 0.04 * letras
    elif len(limpia) >= 2 and limpia.isupper():
        d = 0.08 + 0.15 * len(limpia)          # siglas: "RAM", "DLSS", "OBS"...
    else:
        d = 0.09 + 0.045 * len(limpia)
    if p.endswith("…"):
        d += 0.45
    elif p[-1] in ".:?!":
        d += 0.30
    elif p[-1] in ",;":
        d += 0.12
    return d


def construir_linea_tiempo():
    t = 0.0
    segs = []
    for s in SEGMENTOS:
        palabras = s["voz"].split()
        inicios = []
        for p in palabras:
            inicios.append(t)
            t += dur_palabra(p)
        fin_voz = t
        t += s.get("cola", 0.3)
        seg = dict(s, palabras=palabras, inicios=inicios, t0=inicios[0], fin_voz=fin_voz, t1=t)
        segs.append(seg)
    return segs, t


def ancla(seg, a):
    """Convierte un ancla (0 o frase) en segundos."""
    if a in (0, None):
        return seg["t0"]
    pos = seg["voz"].find(a)
    if pos < 0:
        raise ValueError(f"Ancla '{a}' no encontrada en {seg['id']}")
    idx = len(seg["voz"][:pos].split())
    return seg["inicios"][idx]


def fin_ancla(seg, a):
    return seg["t1"] if a is None else ancla(seg, a)


# ------------------------------------------------------------------ cámara ---
def params(cam):
    if cam[0] == "fit":
        return dict(cx=960.0, cy=960.0, s=W / 1920, scx=540.0, scy=920.0,
                    clip=(0.0, 380.0, 1080.0, 1460.0), fit=True)
    _, cx, cy, h = cam
    s = H / h
    hw, hh = 540 / s, 960 / s
    cx = 960 if hw * 2 >= 1920 else min(max(cx, hw), 1920 - hw)
    cy = 960 if hh * 2 >= 1920 else min(max(cy, hh), 1920 - hh)
    return dict(cx=float(cx), cy=float(cy), s=s, scx=540.0, scy=960.0,
                clip=(0.0, 0.0, float(W), float(H)), fit=False)


def ease(u):
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def mezcla(a, b, u):
    lin = lambda x, y: x + (y - x) * u  # noqa: E731
    return dict(cx=lin(a["cx"], b["cx"]), cy=lin(a["cy"], b["cy"]),
                s=math.exp(lin(math.log(a["s"]), math.log(b["s"]))),
                scx=lin(a["scx"], b["scx"]), scy=lin(a["scy"], b["scy"]),
                clip=tuple(lin(x, y) for x, y in zip(a["clip"], b["clip"])),
                fit=b["fit"] if u > 0.5 else a["fit"])


def con_deriva(p, dt):
    if p["fit"] or dt <= 0:
        return p
    q = dict(p)
    q["s"] = p["s"] * min(1 + 0.012 * dt, 1.10)   # zoom lento tipo "Ken Burns"
    return q


def movimientos(segs):
    movs = []
    for seg in segs:
        for a, cam in seg["camaras"]:
            t = ancla(seg, a)
            if a not in (0, None):
                t -= 0.1
            movs.append((t, params(cam)))
    movs.sort(key=lambda m: m[0])
    return movs


def camaras_por_frame(movs, n):
    out = []
    estado_ini = []
    for i, (t, dst) in enumerate(movs):
        if i == 0:
            estado_ini.append(dst)
            continue
        t_prev, dst_prev = movs[i - 1]
        desde = evaluar(estado_ini[i - 1], dst_prev, t_prev, t, first=(i - 1 == 0))
        estado_ini.append(desde)
    for f in range(n):
        t = f / FPS
        i = max(k for k, m in enumerate(movs) if m[0] <= t) if t >= movs[0][0] else 0
        out.append(evaluar(estado_ini[i], movs[i][1], movs[i][0], t, first=(i == 0)))
    return out


def evaluar(desde, dst, t_ini, t, first=False):
    if first:
        return con_deriva(dst, t - t_ini)
    u = (t - t_ini) / DUR_MOV
    if u < 1:
        return mezcla(desde, dst, ease(max(u, 0)))
    return con_deriva(dst, t - t_ini - DUR_MOV)


def a_pantalla(p, x, y):
    return p["scx"] + (x - p["cx"]) * p["s"], p["scy"] + (y - p["cy"]) * p["s"]


# ------------------------------------------------------------------ dibujo ---
G = {}


def init():
    foto = Image.open(FOTO).convert("RGB")
    G["foto"] = foto
    fondo = foto.crop((420, 0, 1500, 1920)).filter(ImageFilter.GaussianBlur(40))
    G["fondo"] = Image.eval(fondo, lambda v: int(v * 0.33)).convert("RGBA")
    grad = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(grad)
    for y in range(0, 560):
        d.line([(0, y), (W, y)], fill=int(175 * (1 - y / 560) ** 1.6))
    for y in range(1250, H):
        d.line([(0, y), (W, y)], fill=int(215 * ((y - 1250) / (H - 1250)) ** 1.3))
    G["grad"] = grad
    G["negro"] = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    G["f"] = {k: fuente(*k) for k in [("black", 70), ("black", 60), ("semi", 34), ("black", 34),
                                       ("bold", 30), ("semi", 38), ("black", 120), ("black", 104),
                                       ("black", 40), ("semi", 44), ("semi", 24), ("black", 110)]}


def texto_ajustado(d, txt, peso, tam, ancho_max):
    f = fuente(peso, tam)
    while d.textlength(txt, font=f) > ancho_max and tam > 20:
        tam -= 2
        f = fuente(peso, tam)
    return f


def alfa_ventana(t, a, b, fade=0.25):
    if t < a or t > b:
        return 0.0
    return max(0.0, min(1.0, (t - a) / fade, (b - t) / fade))


def pegar_foto(frame, p):
    foto = G["foto"]
    cx0, cy0, cx1, cy1 = p["clip"]
    ix0, iy0 = a_pantalla(p, 0, 0)
    ix1, iy1 = a_pantalla(p, 1920, 1920)
    X0, Y0 = math.ceil(max(cx0, ix0)), math.ceil(max(cy0, iy0))
    X1, Y1 = math.floor(min(cx1, ix1)), math.floor(min(cy1, iy1))
    if X1 - X0 < 2 or Y1 - Y0 < 2:
        return
    sx = lambda X: min(max(p["cx"] + (X - p["scx"]) / p["s"], 0), 1920)  # noqa: E731
    sy = lambda Y: min(max(p["cy"] + (Y - p["scy"]) / p["s"], 0), 1920)  # noqa: E731
    trozo = foto.resize((X1 - X0, Y1 - Y0), Image.BICUBIC, box=(sx(X0), sy(Y0), sx(X1), sy(Y1)))
    frame.paste(trozo, (X0, Y0))


def caja_pantalla(p, caja, pad=14):
    x0, y0 = a_pantalla(p, caja[0], caja[1])
    x1, y1 = a_pantalla(p, caja[2], caja[3])
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def dibujar_resaltes(frame, ov, p, activos, t):
    if not activos:
        return frame
    amax = max(a for a, _ in activos)
    mask = Image.new("L", (W, H), int(125 * amax))
    dm = ImageDraw.Draw(mask)
    d = ImageDraw.Draw(ov)
    pulso = 0.82 + 0.18 * math.sin(2 * math.pi * 1.1 * t)
    for a, caja in activos:
        r = caja_pantalla(p, caja)
        dm.rounded_rectangle(r, radius=22, fill=int(125 * (amax - a)))
    frame = Image.composite(G["negro"], frame, mask)
    for a, caja in activos:
        r = caja_pantalla(p, caja)
        for ancho, k in ((20, 0.16), (11, 0.34), (5, 1.0)):
            rr = (r[0] - ancho / 2, r[1] - ancho / 2, r[2] + ancho / 2, r[3] + ancho / 2)
            d.rounded_rectangle(rr, radius=22 + ancho / 2, outline=ACENTO + (int(255 * a * k * pulso),),
                                width=ancho)
    return frame


def panel(d, caja, a, radio=28):
    d.rounded_rectangle(caja, radius=radio, fill=(10, 12, 20, int(205 * a)))


def dibujar_etiqueta(d, seg, t):
    num, tit, sub = seg["etiqueta"]
    a = alfa_ventana(t, seg["t0"] + 0.2, seg["t1"] - 0.1, 0.3)
    if a <= 0:
        return
    dx = -40 * (1 - min(1, (t - seg["t0"] - 0.2) / 0.35))
    f_num, f_tit = G["f"][("black", 34)], texto_ajustado(d, tit, "black", 60, 860)
    f_sub = texto_ajustado(d, sub, "semi", 34, 880)
    ancho = max(d.textlength(tit, font=f_tit) + 92, d.textlength(sub, font=f_sub)) + 72
    x, y = 48 + dx, 96
    panel(d, (x, y, x + ancho, y + 178), a)
    d.text((x + 36, y + 30), num, font=f_num, fill=ACENTO + (int(255 * a),))
    d.text((x + 36 + 70, y + 18), tit, font=f_tit, fill=(255, 255, 255, int(255 * a)))
    d.text((x + 36, y + 106), sub, font=f_sub, fill=(225, 228, 240, int(255 * a)))


def dibujar_tarjeta(d, seg, t):
    etapas = seg.get("tarjetas", [])
    for i, (an, kicker, linea, grande) in enumerate(etapas):
        t_a = ancla(seg, an) - 0.05
        t_b = ancla(seg, etapas[i + 1][0]) - 0.05 if i + 1 < len(etapas) else seg["t1"] - 0.1
        if not (t_a <= t <= t_b):
            continue
        a = alfa_ventana(t, t_a, t_b, 0.2)
        sube = 30 * (1 - min(1, (t - t_a) / 0.3))
        y = 320 + sube
        panel(d, (48, y, 1032, y + 300), a)
        d.rounded_rectangle((48, y, 1032, y + 300), radius=28, outline=ACENTO + (int(200 * a),), width=4)
        fk = texto_ajustado(d, kicker, "bold", 30, 900)
        fl = texto_ajustado(d, linea, "semi", 38, 900)
        fg = texto_ajustado(d, grande, "black", 120, 920)
        d.text((88, y + 26), kicker, font=fk, fill=ACENTO + (int(255 * a),))
        d.text((88, y + 70), linea, font=fl, fill=(255, 255, 255, int(255 * a)))
        d.text((84, y + 128), grande, font=fg, fill=ACENTO + (int(255 * a),))


def dibujar_titulo(d, a):
    f = G["f"][("black", 104)]
    for txt, y, col in (("¿CÓMO FUNCIONA", 112, (255, 255, 255)), ("UN PC?", 232, ACENTO)):
        w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, y), txt, font=f, fill=col + (int(255 * a),),
               stroke_width=6, stroke_fill=(0, 0, 0, int(255 * a)))


def dibujar_flujo(d, seg, t):
    pasos = seg["flujo"]
    f = G["f"][("black", 40)]
    tiempos = [ancla(seg, a) for a, _ in pasos]
    activo = max([i for i, tt in enumerate(tiempos) if t >= tt], default=-1)
    flecha = "  →  "
    total = sum(d.textlength(n, font=f) + 36 for _, n in pasos) + d.textlength(flecha, font=f) * (len(pasos) - 1)
    x = (W - total) / 2
    y = 250
    for i, (_, n) in enumerate(pasos):
        w = d.textlength(n, font=f) + 36
        if i == activo:
            d.rounded_rectangle((x, y, x + w, y + 64), radius=18, fill=ACENTO + (255,))
            col = (12, 12, 18, 255)
        elif i < activo:
            d.rounded_rectangle((x, y, x + w, y + 64), radius=18, outline=(255, 255, 255, 200), width=3)
            col = (255, 255, 255, 230)
        else:
            col = (255, 255, 255, 90)
        d.text((x + 18, y + 9), n, font=f, fill=col)
        x += w
        if i < len(pasos) - 1:
            d.text((x, y + 9), flecha, font=f, fill=(255, 255, 255, 160))
            x += d.textlength(flecha, font=f)


def trozos_subtitulo(seg):
    """Agrupa palabras en bloques cortos estilo TikTok."""
    bloques, actual = [], []
    for i, p in enumerate(seg["palabras"]):
        actual.append(i)
        txt = " ".join(seg["palabras"][j] for j in actual)
        if len(txt) >= 14 or p[-1] in ".,:?!…;":
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)
    return bloques


def dibujar_subtitulos(d, seg, t):
    for bloque in seg["_bloques"]:
        t_a = seg["inicios"][bloque[0]]
        sig = bloque[-1] + 1
        t_b = seg["inicios"][sig] if sig < len(seg["palabras"]) else seg["t1"]
        if not (t_a <= t < t_b):
            continue
        palabras = [seg["palabras"][j] for j in bloque]
        f = texto_ajustado(d, " ".join(palabras), "black", 70, 960)
        esp = d.textlength(" ", font=f)
        total = sum(d.textlength(p, font=f) for p in palabras) + esp * (len(palabras) - 1)
        x, y = (W - total) / 2, 1585
        for j, p in zip(bloque, palabras):
            ini = seg["inicios"][j]
            fin = seg["inicios"][j + 1] if j + 1 < len(seg["palabras"]) else seg["fin_voz"]
            col = ACENTO if ini <= t < fin else (255, 255, 255)
            d.text((x, y), p, font=f, fill=col + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
            x += d.textlength(p, font=f) + esp


def render(fidx):
    t = fidx / FPS
    p = CAMS[fidx]
    seg = next(s for s in SEGS if s["t0"] <= t < s["t1"]) if t < SEGS[-1]["t1"] else SEGS[-1]
    frame = G["fondo"].copy()
    pegar_foto(frame, p)
    lleno = (p["clip"][3] - p["clip"][1] - 1080) / (1920 - 1080)
    fuerza = 0.35 + 0.65 * max(0.0, min(1.0, lleno))
    frame = Image.composite(G["negro"], frame, G["grad"].point(lambda v: int(v * fuerza)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    activos = []
    for s in SEGS:
        for a0, a1, caja in s["resaltes"]:
            ta, tb = ancla(s, a0), fin_ancla(s, a1)
            al = alfa_ventana(t, ta, tb)
            if al > 0:
                activos.append((al, caja))
    frame = dibujar_resaltes(frame, ov, p, activos, t)
    d = ImageDraw.Draw(ov)
    if seg.get("titulo"):
        dibujar_titulo(d, 1.0)
    if seg.get("etiqueta"):
        dibujar_etiqueta(d, seg, t)
    if seg.get("tarjetas"):
        dibujar_tarjeta(d, seg, t)
    if seg.get("flujo"):
        an, frase = seg["frase_final"]
        if t < ancla(seg, an) - 0.05:
            dibujar_flujo(d, seg, t)
        else:
            a = min(1.0, (t - ancla(seg, an)) / 0.25)
            for txt, fk, y, col in (("FPS", ("black", 110), 140, ACENTO),
                                    ("= fotogramas por segundo", ("semi", 44), 270, (255, 255, 255))):
                f = G["f"][fk]
                d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=col + (int(255 * a),),
                       stroke_width=5, stroke_fill=(0, 0, 0, int(255 * a)))
    dibujar_subtitulos(d, seg, t)
    fc = G["f"][("semi", 24)]
    d.text(((W - d.textlength(CREDITO, font=fc)) / 2, 1872), CREDITO, font=fc, fill=(255, 255, 255, 140))
    frame.alpha_composite(ov)
    return frame.convert("RGB").tobytes()


SEGS, TOTAL = construir_linea_tiempo()
for _s in SEGS:
    _s["_bloques"] = trozos_subtitulo(_s)
N = int(math.ceil(TOTAL * FPS))
CAMS = camaras_por_frame(movimientos(SEGS), N)


def srt_tiempo(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def escribir_srt_y_tiempos():
    lineas, k = [], 1
    for s in SEGS:
        for b in s["_bloques"]:
            ta = s["inicios"][b[0]]
            sig = b[-1] + 1
            tb = s["inicios"][sig] if sig < len(s["palabras"]) else s["fin_voz"] + 0.2
            lineas += [str(k), f"{srt_tiempo(ta)} --> {srt_tiempo(tb)}",
                       " ".join(s["palabras"][j] for j in b), ""]
            k += 1
    with open(os.path.join(SALIDA, "subtitulos.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas))
    tiempos = [dict(id=s["id"], nombre=s["nombre"], inicio=round(s["t0"], 2), fin=round(s["t1"], 2),
                    palabras=len(s["palabras"])) for s in SEGS]
    with open(os.path.join(SALIDA, "tiempos.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(total=round(TOTAL, 2), segmentos=tiempos), fh, ensure_ascii=False, indent=1)
    return tiempos


def main():
    os.makedirs(SALIDA, exist_ok=True)
    tiempos = escribir_srt_y_tiempos()
    for x in tiempos:
        print(f"{x['inicio']:7.2f}-{x['fin']:7.2f}  {x['nombre']} ({x['palabras']} palabras)")
    print(f"Total: {TOTAL:.1f} s, {N} fotogramas")
    if "--solo-tiempos" in sys.argv:
        return
    destino = os.path.join(SALIDA, "como-funciona-un-pc_borrador.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
           "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-tune", "stillimage",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", destino]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = range(N)
    if "--prueba" in sys.argv:
        frames = [int(x) for x in sys.argv[sys.argv.index("--prueba") + 1].split(",")]
        init()
        for f in frames:
            Image.frombytes("RGB", (W, H), render(f)).save(os.path.join(SALIDA, f"prueba_{f}.jpg"), quality=88)
        ff.stdin.close()
        ff.kill()
        return
    with Pool(os.cpu_count(), initializer=init) as pool:
        for i, datos in enumerate(pool.imap(render, frames, chunksize=6)):
            ff.stdin.write(datos)
            if i % 300 == 0:
                print(f"  fotograma {i}/{N}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("Listo:", destino)


if __name__ == "__main__":
    main()
