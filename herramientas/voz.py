# -*- coding: utf-8 -*-
"""Genera la voz en off del guion con Piper (TTS local, de código abierto) y calcula
cuándo empieza cada palabra, para que los subtítulos y los zooms del vídeo vayan sincronizados.

Uso:  python3 herramientas/voz.py [--voz RUTA.onnx] [--hablante N] [--velocidad 0.9]
Salida: video/voz.wav y video/voz_tiempos.json (los usa render_video.py)

Voz por defecto: es_ES-davefx-medium (español de España, licencia CC0), descargada de
https://huggingface.co/rhasspy/piper-voices  (archivos .onnx y .onnx.json en la misma carpeta).
"""
import argparse
import json
import os
import re
import sys
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guion_data import SEGMENTOS  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cómo se tiene que PRONUNCIAR cada palabra que se escribe distinto (el subtítulo no cambia).
PRONUNCIACION = {
    "5070": "cincuenta setenta",
    "Ti": "te i",
    "OBS": "o be ese",
    "RAM": "ram",
    "Fortnite": "fórnait",
    "Cyberpunk": "sáiber pank",
    "Chrome": "crom",
    "Discord": "díscord",
    "Windows": "güíndous",
    "path": "pas",
    "tracing": "tréisin",
    "gaming": "gueimin",
    "Samsung": "sámsung",
    "Express": "express",
    "PCI": "pe ce i",
    "Intel": "íntel",
    "SSD": "esesedé",
    "DDR5": "de de erre cinco",
    "DLSS": "el de ele ese ese",
}

# Retoques de frase completa solo para la voz (añadir una pausa donde ayuda a entenderlo).
AJUSTES_FRASE = [
    ("Por eso sáiber pank,", "Por eso, sáiber pank,"),
]

PUNT_FIN = ".?!…"
PAUSA_TRAS = {".": 0.20, "?": 0.24, "!": 0.22, "…": 0.38}
PAUSA_ENTRE_SEGMENTOS = 0.30


def hablado(token):
    """Devuelve el texto a sintetizar para un token del guion (con su puntuación)."""
    m = re.match(r"^([¿¡]*)(.*?)([.,:;?!…]*)$", token)
    pre, cuerpo, post = m.groups()
    cuerpo = PRONUNCIACION.get(cuerpo, cuerpo)
    if post == "…":
        post = ","          # el "…" se hace con una pausa propia; la entonación queda en suspenso
    return pre + cuerpo + post


def frases(tokens):
    """Agrupa los índices de tokens en frases (cada una se sintetiza por separado)."""
    out, actual = [], []
    for i, t in enumerate(tokens):
        actual.append(i)
        if t[-1] in PUNT_FIN:
            out.append(actual)
            actual = []
    if actual:
        out.append(actual)
    return out


def recortar(audio, sr, umbral_db=-42, margen=0.03):
    env = np.abs(audio)
    lim = env.max() * 10 ** (umbral_db / 20)
    idx = np.where(env > lim)[0]
    if len(idx) == 0:
        return audio
    a = max(idx[0] - int(margen * sr), 0)
    b = min(idx[-1] + int(margen * sr), len(audio))
    return audio[a:b]


def silencios(audio, sr, min_dur=0.07):
    """Pausas internas (inicio, fin) en segundos, detectadas por energía."""
    hop = int(0.01 * sr)
    n = len(audio) // hop
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    lim = rms.max() * 0.06
    silencio = rms < lim
    out, i = [], 0
    while i < n:
        if silencio[i]:
            j = i
            while j < n and silencio[j]:
                j += 1
            if (j - i) * 0.01 >= min_dur and i > 5 and j < n - 5:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def pesos(voz, tokens_hablados):
    """Duración relativa de cada palabra ≈ número de fonemas."""
    out = []
    for t in tokens_hablados:
        limpio = re.sub(r"[¿¡.,:;?!…]", "", t)
        fon = "".join("".join(s) for s in voz.phonemize(limpio)) if limpio else ""
        out.append(len(re.sub(r"[ˈˌ\s]", "", fon)) + 1.5)
    return out


def tiempos_frase(tokens, idxs, pesos_tok, dur, pausas):
    """Reparte el tiempo de la frase entre sus palabras usando las pausas de las comas como anclas."""
    total = sum(pesos_tok[i] for i in idxs)
    # estimación proporcional inicial
    acum, est = 0.0, {}
    for i in idxs:
        est[i] = acum / total * dur
        acum += pesos_tok[i]
    # comas / dos puntos internos -> buscar la pausa detectada más cercana
    anclas = []  # (posición en idxs de la palabra que va DESPUÉS de la pausa, inicio_pausa, fin_pausa)
    usadas = set()
    for k, i in enumerate(idxs[:-1]):
        if tokens[i][-1] in ",:;…":
            esperado = est[idxs[k + 1]]
            cand = [(abs((a + b) / 2 - esperado), n) for n, (a, b) in enumerate(pausas) if n not in usadas]
            if cand:
                d, n = min(cand)
                if d < 0.9:
                    usadas.add(n)
                    anclas.append((k + 1, pausas[n][0], pausas[n][1]))
    anclas.sort()
    # tramos entre anclas
    limites = [(0, 0.0)] + [(k, b) for k, a, b in anclas]
    fines = [a for k, a, b in anclas] + [dur]
    inicios = {}
    for (k0, t0), t1, k1 in zip(limites, fines, [k for k, _, _ in anclas] + [len(idxs)]):
        tramo = idxs[k0:k1]
        tot = sum(pesos_tok[i] for i in tramo) or 1
        acc = 0.0
        for i in tramo:
            inicios[i] = t0 + acc / tot * (t1 - t0)
            acc += pesos_tok[i]
    return inicios, len(anclas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voz", default=os.path.join(RAIZ, "voces", "es_ES-davefx-medium.onnx"))
    ap.add_argument("--hablante", type=int, default=None)
    ap.add_argument("--velocidad", type=float, default=0.9, help="length_scale de Piper (<1 = más rápido)")
    args = ap.parse_args()

    voz = PiperVoice.load(args.voz)
    sr = voz.config.sample_rate
    cfg = SynthesisConfig(length_scale=args.velocidad, speaker_id=args.hablante)
    pista = []
    t = 0.0
    salida = []
    for nseg, seg in enumerate(SEGMENTOS):
        tokens = seg["voz"].split()
        habl = [hablado(x) for x in tokens]
        pw = pesos(voz, habl)
        inicios = [0.0] * len(tokens)
        lista_frases = frases(tokens)
        for nfr, idxs in enumerate(lista_frases):
            texto = " ".join(habl[i] for i in idxs)
            for viejo, nuevo in AJUSTES_FRASE:
                texto = texto.replace(viejo, nuevo)
            audio = np.concatenate([c.audio_float_array for c in voz.synthesize(texto, syn_config=cfg)])
            audio = recortar(audio, sr)
            dur = len(audio) / sr
            rel, n_anclas = tiempos_frase(tokens, idxs, pw, dur, silencios(audio, sr))
            for i in idxs:
                inicios[i] = round(t + rel[i], 3)
            pista.append(audio)
            t += dur
            ultimo = nseg == len(SEGMENTOS) - 1 and nfr == len(lista_frases) - 1
            pausa = 0.0 if ultimo else PAUSA_TRAS.get(tokens[idxs[-1]][-1], 0.12)
            pista.append(np.zeros(int(pausa * sr), dtype=np.float32))
            fin_voz = t
            t += pausa
            print(f"  [{seg['id']}] {dur:5.2f}s  anclas={n_anclas}  {texto[:70]}")
        if nseg < len(SEGMENTOS) - 1:
            pista.append(np.zeros(int(PAUSA_ENTRE_SEGMENTOS * sr), dtype=np.float32))
            t += PAUSA_ENTRE_SEGMENTOS
        salida.append(dict(id=seg["id"], inicios=inicios, fin_voz=round(fin_voz, 3), t1=round(t, 3)))
    salida[-1]["t1"] = round(salida[-1]["fin_voz"] + 0.08, 3)   # corte seco para el bucle
    audio = np.concatenate(pista)
    audio = audio / max(np.abs(audio).max(), 1e-6) * 0.95
    os.makedirs(os.path.join(RAIZ, "video"), exist_ok=True)
    with wave.open(os.path.join(RAIZ, "video", "voz.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    with open(os.path.join(RAIZ, "video", "voz_tiempos.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(voz=os.path.basename(args.voz), hablante=args.hablante, velocidad=args.velocidad,
                       sample_rate=sr, segmentos=salida), fh, ensure_ascii=False, indent=1)
    print(f"Voz: {len(audio) / sr:.1f} s -> video/voz.wav")


if __name__ == "__main__":
    main()
