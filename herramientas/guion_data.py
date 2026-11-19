# -*- coding: utf-8 -*-
"""Texto del guion + planos de cámara sobre la foto.

Todas las coordenadas están en píxeles de imagenes/pc-interior-original.jpg (1920x1920).
Si cambias aquí el texto, vuelve a ejecutar render_video.py y se regeneran
el vídeo borrador y los subtítulos con los tiempos nuevos.
"""

# --- Cajas de cada componente (x0, y0, x1, y1) en la foto -------------------
PLACA = (93, 253, 1037, 1188)
BOMBA_CPU = (505, 455, 810, 714)        # bloque be quiet! (debajo está el procesador)
TUBOS = (780, 130, 1500, 780)
RADIADOR = (1480, 200, 1900, 1650)      # radiador 360 mm + ventiladores del frontal
RAM = (841, 346, 943, 784)
SSD = (371, 771, 662, 844)              # disipador "CTRL + WASD" encima del SSD M.2
GRAFICA = (80, 848, 1443, 1270)
FUENTE = (300, 1300, 1000, 1880)        # cubierta inferior: la fuente va escondida aquí
CABLE_24P = (985, 440, 1110, 680)
CABLE_EPS = (288, 176, 448, 272)
CABLE_16P = (740, 960, 825, 1425)

# --- Cámaras -------------------------------------------------------------------
# FIT        -> la foto entera, centrada (plano general)
# ("v", cx, cy, alto) -> plano vertical 9:16 a pantalla completa centrado en (cx, cy)
FIT = ("fit",)


def V(cx, cy, h):
    return ("v", cx, cy, h)


# --- Segmentos -----------------------------------------------------------------
# Las "anclas" son el inicio de una frase dentro de "voz" (o 0 = inicio del segmento).
SEGMENTOS = [
    dict(
        id="inicio",
        nombre="Gancho",
        voz="¿Cómo funciona un PC? Este PC gaming lleva por dentro una RTX 5070 Ti, "
            "un Intel i9-14900K y 64 gigas de RAM DDR5. Vamos pieza a pieza.",
        titulo=True,
        camaras=[(0, FIT)],
        resaltes=[("una RTX", "un Intel", GRAFICA), ("un Intel", "y 64", BOMBA_CPU),
                  ("y 64", "Vamos", RAM)],
    ),
    dict(
        id="placa",
        nombre="Placa base",
        etiqueta=("01", "PLACA BASE", "ASUS ROG Strix Z690-F Gaming WiFi"),
        voz="Todo va enchufado a la placa base. Es como una ciudad: cada pieza tiene su sitio "
            "y se hablan por miles de pistas de cobre, como carreteras.",
        camaras=[(0, V(565, 900, 1800))],
        resaltes=[(0, None, PLACA)],
    ),
    dict(
        id="cpu",
        nombre="Procesador",
        etiqueta=("02", "PROCESADOR · CPU", "Intel Core i9-14900K · 24 núcleos · 6,0 GHz"),
        voz="Debajo de este bloque está el cerebro: el procesador. Un i9-14900K con 24 núcleos "
            "y hasta 6 gigahercios. Calcula todo lo que pasa en la partida: cada jugador, cada "
            "disparo, cada construcción. Por eso en Fortnite, en modo rendimiento, que es donde "
            "más trabaja el procesador, este PC va a unos 400 o 500 FPS.",
        camaras=[(0, V(640, 600, 980)), ("Por eso", V(655, 640, 1150))],
        resaltes=[(0, None, BOMBA_CPU)],
        tarjetas=[("Por eso", "POR ESO…", "Fortnite · Modo rendimiento · 1080p", "≈ 400–500 FPS")],
    ),
    dict(
        id="refrigeracion",
        nombre="Refrigeración",
        etiqueta=("03", "REFRIGERACIÓN LÍQUIDA", "be quiet! Light Loop 360 mm"),
        voz="Y como puede gastar hasta 250 vatios, se calienta muchísimo. Por eso lleva "
            "refrigeración líquida: la bomba mueve el líquido por estos dos tubos hasta un radiador "
            "de 360 milímetros, y los ventiladores sacan el calor fuera.",
        camaras=[(0, V(700, 600, 1100)), ("por estos dos", V(1140, 520, 1300)),
                 ("hasta un radiador", V(1580, 900, 1800))],
        resaltes=[(0, "por estos dos", BOMBA_CPU), ("por estos dos", "hasta un radiador", TUBOS),
                  ("hasta un radiador", None, RADIADOR)],
    ),
    dict(
        id="ram",
        nombre="RAM",
        etiqueta=("04", "MEMORIA RAM", "G.Skill Trident Z5 RGB · 64 GB DDR5-6000 CL30"),
        voz="Estas dos barras con luces son la RAM: 64 gigas DDR5. Es la mesa de trabajo del "
            "procesador: lo que estás usando se carga aquí, porque es muchísimo más rápida que el "
            "disco. Y van dos para trabajar en doble canal: el doble de carriles. Por eso puedes "
            "tener Fortnite, Discord, Chrome y OBS grabando a la vez sin que se trabe.",
        camaras=[(0, V(900, 600, 960)), ("Por eso", V(892, 600, 1150))],
        resaltes=[(0, None, RAM)],
        tarjetas=[("Por eso", "POR ESO…", "Fortnite + Discord + Chrome + OBS", "64 GB")],
    ),
    dict(
        id="ssd",
        nombre="SSD",
        etiqueta=("05", "ALMACENAMIENTO · SSD", "Samsung 990 Pro 1 TB · NVMe PCIe 4.0"),
        voz="Aquí, bajo este disipador, está el disco: un SSD Samsung 990 Pro, conectado directo "
            "al procesador, que lee a más de 7.000 megas por segundo: unas 50 veces más que un disco "
            "duro antiguo. Por eso Windows arranca en segundos y las partidas cargan casi al instante.",
        camaras=[(0, V(520, 830, 900))],
        resaltes=[(0, None, SSD)],
        tarjetas=[("lee a más", "VELOCIDAD DE LECTURA", "≈ 50 veces un disco duro", "7.450 MB/s"),
                  ("Por eso", "POR ESO…", "Windows y partidas", "en segundos")],
    ),
    dict(
        id="grafica",
        nombre="Gráfica",
        etiqueta=("06", "TARJETA GRÁFICA · GPU", "Gigabyte RTX 5070 Ti AERO OC · 16 GB GDDR7"),
        voz="Y esta bestia es la tarjeta gráfica: una RTX 5070 Ti con 16 gigas de memoria propia. "
            "Va pinchada en la ranura PCI Express y tiene casi 9.000 núcleos que dibujan cada imagen "
            "que ves, cientos de veces por segundo. Ojo: el monitor se conecta a la gráfica, no a la "
            "placa. Por eso Cyberpunk, a 1440p con path tracing, va a unos 40 FPS a pelo… pero con "
            "DLSS 4 y generación de fotogramas pasa de 150.",
        camaras=[(0, V(430, 960, 1250)), ("Va pinchada", V(1110, 960, 1250)),
                 ("Ojo:", V(400, 960, 1250)), ("Por eso", V(760, 1000, 1400))],
        resaltes=[(0, None, GRAFICA)],
        tarjetas=[("Ojo:", "ERROR TÍPICO", "El monitor se enchufa a la gráfica", "NO a la placa"),
                  ("Por eso", "POR ESO…", "Cyberpunk 2077 · 1440p · Path tracing", "≈ 40 FPS"),
                  ("pero con DLSS", "CON DLSS 4 + GENERACIÓN DE FOTOGRAMAS",
                   "Cyberpunk 2077 · 1440p · Path tracing", "+150 FPS")],
    ),
    dict(
        id="fuente",
        nombre="Fuente y cables",
        etiqueta=("07", "FUENTE DE ALIMENTACIÓN", "Escondida bajo la cubierta · recomendada ≈ 850 W"),
        voz="¿Y la energía? Aquí abajo, escondida, está la fuente de alimentación: convierte los "
            "230 voltios del enchufe en 12 y los reparte por cables. Este gordo de 24 pines va a la "
            "placa, estos de arriba al procesador, y este de 16 pines a la gráfica, que ella sola "
            "se traga 300 vatios.",
        camaras=[(0, V(650, 1270, 1300)), ("Este gordo", V(1050, 560, 900)),
                 ("estos de arriba", V(400, 500, 1100)), ("y este de 16", V(782, 1150, 1050))],
        resaltes=[(0, "Este gordo", FUENTE), ("Este gordo", "estos de arriba", CABLE_24P),
                  ("estos de arriba", "y este de 16", CABLE_EPS), ("y este de 16", None, CABLE_16P)],
        tarjetas=[("que ella sola", "CONSUMO DE LA GRÁFICA", "Fuente recomendada: ~850 W", "300 W")],
    ),
    dict(
        id="resumen",
        nombre="Resumen",
        voz="Así que, cuando juegas: el SSD carga el juego en la RAM, el procesador calcula qué pasa, "
            "y la gráfica lo dibuja y lo manda al monitor. Cada vez que hace eso es un fotograma, "
            "y los que hace en un segundo… son tus FPS.",
        camaras=[(0, FIT)],
        resaltes=[("el SSD", "en la RAM", SSD), ("en la RAM", "el procesador", RAM),
                  ("el procesador", "y la gráfica", BOMBA_CPU), ("y la gráfica", "Cada vez", GRAFICA)],
        flujo=[("el SSD", "SSD"), ("en la RAM", "RAM"), ("el procesador", "CPU"),
               ("y la gráfica", "GPU"), ("y lo manda", "MONITOR")],
        frase_final=("y los que", "FPS = FOTOGRAMAS POR SEGUNDO"),
    ),
    dict(
        id="bucle",
        nombre="Final en bucle",
        voz="Y por eso, ahora ya sabes…",
        camaras=[(0, FIT)],
        resaltes=[],
        cola=0.05,   # corte seco: el vídeo vuelve a empezar con "¿Cómo funciona un PC?"
    ),
]
