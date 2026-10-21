#!/usr/bin/env python3
"""Create an ORIGINAL Mundo al Día vertical video draft from editor-verified Spanish text.
Uses licensed context photos and a local Spanish neural TTS voice. No publication side effects.
"""
import argparse
import os
import re
import subprocess
import textwrap
import json
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
OUT = Path("video-draft-output")
NAVY = (8, 22, 48)
BLUE = (18, 74, 130)
CYAN = (43, 198, 220)
WHITE = (248, 250, 252)
MUTED = (202, 218, 234)
PHOTO_PATHS = []
PHOTO_CREDITS = []


def download_verified_commons_photo(out_dir, search_query, filename):
    """Download a real Commons photo after checking its file-page license metadata."""
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "file:" + search_query, "gsrnamespace": 6,
        "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1400,
    })
    req = urllib.request.Request(api, headers={"User-Agent": "MundoAlDiaDraftGenerator/1.0 (editorial test)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    pages = (data.get("query", {}).get("pages", {}) or {}).values()
    accepted = {"public domain", "cc0", "cc by 4.0", "cc by 3.0", "cc by 2.0", "cc by 1.0"}
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        license_name = (meta.get("LicenseShortName", {}).get("value", "") or "").strip()
        license_lower = license_name.lower()
        if not any(term in license_lower for term in accepted):
            continue
        image_url = info.get("thumburl") or info.get("url")
        if not image_url:
            continue
        title = page.get("title", "Wikimedia Commons image")
        artist = meta.get("Artist", {}).get("value", "Author not listed")
        credit = re.sub(r"<[^>]+>", "", artist).strip()
        page_url = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/:()")
        out_path = out_dir / filename
        request = urllib.request.Request(image_url, headers={"User-Agent": "MundoAlDiaDraftGenerator/1.0 (editorial test)"})
        with urllib.request.urlopen(request, timeout=30) as response, out_path.open("wb") as target:
            target.write(response.read())
        return {
            "path": out_path,
            "file": title,
            "source": page_url,
            "license": license_name,
            "credit": credit or "No indicado",
            "search": search_query,
        }
    raise RuntimeError(f"No se encontró una foto pertinente con licencia aceptada para: {search_query}")


def save_photo_credits(out_dir, credits):
    lines = [
        "FUENTES Y LICENCIAS DE FOTOGRAFÍAS — borrador no publicado.",
        "Las imágenes son fotos reales de contexto; comprobar pertinencia visual antes de publicar.",
        "",
    ]
    for i, item in enumerate(credits, 1):
        lines.extend([
            f"Escena {i}: {item['search']}",
            f"Archivo: {item['file']}",
            f"Fuente: {item['source']}",
            f"Licencia declarada: {item['license']}",
            f"Autor/crédito: {item['credit']}",
            "",
        ])
    (out_dir / "FUENTE_Y_LICENCIA_FOTO.txt").write_text("\n".join(lines), encoding="utf-8")


def run(args):
    subprocess.run(args, check=True)


def font(size, bold=False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_by_pixels(draw, text, fnt, max_width):
    words = re.sub(r"\s+", " ", text.strip()).split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def split_narration(text, parts=3):
    words = text.split()
    if not words:
        return ["Información en desarrollo."]
    chunks = []
    for i in range(parts):
        start = round(i * len(words) / parts)
        end = round((i + 1) * len(words) / parts)
        if start < end:
            chunks.append(" ".join(words[start:end]))
    return chunks


def draw_visual(im, d, body, index):
    """Use a wide, restrained photo frame so the story text has room below."""
    x0, y0, x1, y1 = 72, 570, 1008, 1040
    if not PHOTO_PATHS:
        raise RuntimeError("No hay fotos con licencia revisable; no se genera un vídeo con imágenes ficticias.")
    photo_path = PHOTO_PATHS[min(max(index - 1, 0), len(PHOTO_PATHS) - 1)]
    if not Path(photo_path).exists():
        raise RuntimeError("Falta una foto descargada y verificada.")
    photo = Image.open(photo_path).convert("RGB")
    tw, th = x1 - x0, y1 - y0
    scale = max(tw / photo.width, th / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.Resampling.LANCZOS)
    left = (photo.width - tw) // 2
    top = (photo.height - th) // 2
    im.paste(photo.crop((left, top, left + tw, top + th)), (x0, y0))
    d.rectangle((x0, y0, x1, y1), outline=WHITE, width=2)
    d.text((x0 + 8, y1 + 10), "FOTO REAL DE CONTEXTO · VER FUENTE Y LICENCIA", font=font(17, True), fill=MUTED)


def draw_scene(path, title, body, index, total, end_card=False):
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[k] * (1 - t) + BLUE[k] * t) for k in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 22), fill=CYAN)
    d.ellipse((760, -190, 1260, 310), outline=(35, 112, 165), width=5)
    d.ellipse((-220, 1400, 220, 1840), outline=(35, 112, 165), width=5)
    d.rounded_rectangle((66, 72, 440, 145), radius=28, fill=CYAN)
    d.text((92, 84), "MUNDO AL DÍA", font=font(34, True), fill=NAVY)
    d.text((72, 190), "NOTICIAS INTERNACIONALES", font=font(25, True), fill=MUTED)
    title_lines = wrap_by_pixels(d, title, font(52, True), 920)
    y = 270
    for line in title_lines[:5]:
        d.text((72, y), line, font=font(52, True), fill=WHITE, stroke_width=0)
        y += 69
    d.rounded_rectangle((72, y + 12, 220, y + 23), radius=5, fill=CYAN)
    y += 80
    if not end_card:
        draw_visual(im, d, body, index)
        y = 1110
        max_width = 920
        available_height = 570
    else:
        y = 430
        max_width = 920
        available_height = 760
    # Reduce font size as needed; never silently cut the end of a sentence.
    body_font = font(34)
    body_lines = wrap_by_pixels(d, body, body_font, max_width)
    while len(body_lines) * 45 > available_height and body_font.size > 24:
        body_font = font(body_font.size - 2)
        body_lines = wrap_by_pixels(d, body, body_font, max_width)
    line_h = body_font.size + 12
    if len(body_lines) * line_h > available_height:
        raise RuntimeError(f"El texto de la escena {index} no cabe completo; acorta el texto en lugar de cortarlo.")
    for line in body_lines:
        d.text((80, y), line, font=body_font, fill=WHITE)
        y += line_h
    if end_card:
        d.rounded_rectangle((72, 1450, 1008, 1650), radius=30, fill=(5, 17, 37), outline=CYAN, width=3)
        d.text((110, 1492), "EL MUNDO, AL DÍA.", font=font(48, True), fill=WHITE)
        d.text((110, 1570), "Sigue la página para más información", font=font(27), fill=MUTED)
    else:
        d.text((72, 1740), "INFORMACIÓN EN ESPAÑOL · MUNDO AL DÍA", font=font(24, True), fill=MUTED)
        d.text((930, 1815), f"{index:02d}/{total:02d}", font=font(25, True), fill=CYAN)
    im.save(path, quality=95)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--narration", required=True)
    args = ap.parse_args()
    title = args.title.strip()
    summary = args.summary.strip()
    narration = args.narration.strip()
    if not title or len(title) > 180:
        raise SystemExit("El titular debe tener entre 1 y 180 caracteres.")
    if len(summary) < 60 or len(summary) > 1200:
        raise SystemExit("El resumen debe tener entre 60 y 1200 caracteres.")
    if len(narration) < 100 or len(narration) > 2600:
        raise SystemExit("La narración debe tener entre 100 y 2600 caracteres.")
    OUT.mkdir(parents=True, exist_ok=True)
    global PHOTO_PATHS, PHOTO_CREDITS
    photo_specs = [
        ("White House exterior North Portico exterior building", "foto_casa_blanca.jpg"),
        ("Meeting with Foreign Minister of Iran Abbas Araghchi", "foto_reunion_diplomatica.jpg"),
        ("oil tanker commercial shipping Strait of Hormuz", "foto_estrecho_hormuz.jpg"),
    ]
    PHOTO_CREDITS = [download_verified_commons_photo(OUT, query, filename) for query, filename in photo_specs]
    PHOTO_PATHS = [item["path"] for item in PHOTO_CREDITS]
    save_photo_credits(OUT, PHOTO_CREDITS)
    voice = os.environ.get("MUNDO_AL_DIA_TTS_VOICE", "es-US-AlonsoNeural")
    rate = os.environ.get("MUNDO_AL_DIA_TTS_RATE", "-8%")
    # Split narration into three matching voice/text segments. Each still uses the
    # exact duration of its own generated speech; the end card starts after speech.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()]
    if len(sentences) < 3:
        sentences = split_narration(narration, 3)
    groups = [[] for _ in range(3)]
    for i, sentence in enumerate(sentences):
        groups[min(2, int(i * 3 / len(sentences)))].append(sentence)
    narration_chunks = [" ".join(g).strip() for g in groups if g]
    audio_parts = []
    durations = []
    for i, chunk in enumerate(narration_chunks, 1):
        part = OUT / f"voz_{i:02d}.mp3"
        run(["edge-tts", "--voice", voice, f"--rate={rate}", "--pitch=-2Hz",
             "--text", chunk, "--write-media", str(part)])
        duration = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(part)
        ], text=True).strip())
        audio_parts.append(part)
        durations.append(duration)
    audio = OUT / "narracion_es.mp3"
    audio_list = OUT / "audio_partes.txt"
    with audio_list.open("w", encoding="utf-8") as f:
        for part in audio_parts:
            f.write(f"file '{part.resolve()}'\n")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
         "-safe", "0", "-i", str(audio_list), "-c", "copy", str(audio)])
    scene_paths = []
    for i, chunk in enumerate(narration_chunks, 1):
        p = OUT / f"escena_{i:02d}.png"
        draw_scene(p, title, chunk, i, len(narration_chunks) + 1, end_card=False)
        scene_paths.append(p)
    end_card_path = OUT / f"escena_{len(scene_paths)+1:02d}.png"
    draw_scene(end_card_path, title, "El mundo, al día.", len(scene_paths)+1,
               len(scene_paths)+1, end_card=True)
    scene_paths.append(end_card_path)
    concat = OUT / "escenas.txt"
    with concat.open("w", encoding="utf-8") as f:
        for p, dur in zip(scene_paths[:-1], durations):
            f.write(f"file '{p.resolve()}'\n")
            f.write(f"duration {dur:.3f}\n")
        f.write(f"file '{scene_paths[-1].resolve()}'\n")
        f.write("duration 2.000\n")
        f.write(f"file '{scene_paths[-1].resolve()}'\n")
    video = OUT / "mundo-al-dia-video-original.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(audio),
        "-vf", "fps=30,format=yuv420p", "-af", "apad=pad_dur=2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-t", f"{sum(durations)+2:.3f}",
        "-movflags", "+faststart", str(video)
    ])
    (OUT / "README.txt").write_text(
        "Borrador original de Mundo al Día.\n"
        f"Voz neural usada: {voice}; velocidad: {rate}; tono: -2 Hz.\n"
        "Revisar FUENTE_Y_LICENCIA_FOTO.txt y confirmar pertinencia antes de publicar.\n"
        "Este archivo NO se publicó en el sitio, Facebook ni Instagram.\n"
        "Revisión editorial humana requerida antes de cualquier publicación.\n",
        encoding="utf-8"
    )
    print(f"VIDEO_GENERADO={video}")
    print(f"VOZ_USADA={voice}")
    print(f"DURACION_NARRACION_SEGUNDOS={sum(durations):.1f}")
    print("PUBLICADO=NO")


if __name__ == "__main__":
    main()
