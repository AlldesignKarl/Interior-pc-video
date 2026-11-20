# Interior PC – vídeo "¿Cómo funciona un PC?"

Guion y material para un vídeo vertical en bucle que explica el interior de un PC gaming actual (RTX 5070 Ti, i9-14900K, 64 GB DDR5) pieza a pieza, con ejemplos de FPS.

- **[GUION.md](GUION.md)**: guion completo por bloques (plano, voz y texto en pantalla), versión teleprompter, trucos para el bucle y fuentes de los FPS.
- **`imagenes/`**: foto original, foto anotada y planos verticales de cada pieza.
- **`video/como-funciona-un-pc.mp4`**: el vídeo final 1080×1920 con voz en off y subtítulos (más `voz.wav` y `subtitulos.srt` sueltos).
- **`herramientas/`**: scripts para regenerar todo si cambias el texto: `python3 herramientas/voz.py` (voz), `python3 herramientas/render_video.py` (vídeo) y `python3 herramientas/imagenes.py` (imágenes). Necesitan `pip install piper-tts pillow numpy` y ffmpeg. El modelo de voz (`es_ES-davefx-medium.onnx`, 63 MB) no está en el repo: descárgalo de https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/davefx/medium a la carpeta `voces/`.

Foto: Jacek Halicki, CC BY-SA 4.0, Wikimedia Commons.
