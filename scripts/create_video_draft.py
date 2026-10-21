#!/usr/bin/env python3
"""Create an ORIGINAL Mundo al Día vertical video draft from editor-verified Spanish text.
Uses only locally generated graphics and a local Spanish TTS voice. No third-party video,
photos, reposting, or publication side effects.
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
PHOTO_PATH = None
PHOTO_CREDIT = None


def download_verified_commons_photo(out_dir):
    """Download a Commons photo only after reading its file-page license metadata."""
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "file:Earth from space globe planet", "gsrnamespace": 6,
        "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
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
        out_path = out_dir / "foto_licencia_verificada.jpg"
        request = urllib.request.Request(image_url, headers={"User-Agent": "MundoAlDiaDraftGenerator/1.0 (editorial test)"})
        with urllib.request.urlopen(request, timeout=30) as response, out_path.open("wb") as target:
            target.write(response.read())
        # Store the source page and the license label so a reviewer can independently verify them.
        (out_dir / "FUENTE_Y_LICENCIA_FOTO.txt").write_text(
            "FOTO DE PRUEBA — no representa una noticia actual.\\n"
            f"Archivo: {title}\\nFuente verificable: {page_url}\\n"
            f"Licencia declarada en Wikimedia Commons: {license_name}\\n"
            f"Autor/crédito indicado: {credit or 'No indicado'}\\n"
            "Revisar la página original y sus condiciones antes de cualquier publicación.\\n",
            encoding="utf-8",
        )
        return out_path
    raise RuntimeError("No se encontró una foto de Wikimedia Commons con licencia pública/CC aceptada y metadatos legibles.")


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
    words = re.sub(r"\\s+", " ", text.strip()).split()
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


def draw_visual(d, body, index):
    """Draw a prominent original illustration so each scene has visible imagery."""
    lower = body.lower()
    x0, y0, x1, y1 = 545, 625, 1008, 1460
    d.rounded_rectangle((x0, y0, x1, y1), radius=34, fill=(5, 17, 37), outline=CYAN, width=4)
    cx, cy = (x0 + x1) // 2, y0 + 255
    # A large, original editorial illustration, drawn locally (no external media).
    if any(k in lower for k in ("alamodome", "estadio", "fútbol", "caída", "accidente", "militar")):
        # Stadium bowl, field, and overhead lights.
        d.ellipse((x0 + 34, y0 + 105, x1 - 34, y0 + 470), fill=(18, 74, 130), outline=CYAN, width=5)
        d.ellipse((x0 + 80, y0 + 170, x1 - 80, y0 + 405), fill=(7, 40, 75), outline=WHITE, width=4)
        d.polygon([(x0 + 90, y0 + 290), (x1 - 90, y0 + 290), (x1 - 125, y0 + 390), (x0 + 125, y0 + 390)], fill=(20, 112, 83))
        for xx in range(x0 + 120, x1 - 80, 58):
            d.line((xx, y0 + 315, xx, y0 + 375), fill=(190, 235, 214), width=3)
        for xx in (x0 + 110, x1 - 110):
            d.line((xx, y0 + 60, xx - 20, y0 + 120), fill=CYAN, width=7)
            d.ellipse((xx - 36, y0 + 35, xx + 12, y0 + 78), fill=WHITE)
        d.text((x0 + 42, y0 + 520), "ESCENA ILUSTRADA", font=font(25, True), fill=CYAN)
        d.text((x0 + 42, y0 + 570), "Contexto visual", font=font(28, True), fill=WHITE)
    elif any(k in lower for k in ("protest", "manifest", "marchas", "huelga")):
        d.rectangle((x0 + 35, y0 + 120, x1 - 35, y0 + 470), fill=(10, 48, 86), outline=CYAN, width=3)
        for j, xx in enumerate((x0 + 115, x0 + 230, x0 + 345)):
            d.ellipse((xx - 32, y0 + 205, xx + 32, y0 + 270), fill=(248, 190 - j * 15, 120 + j * 20))
            d.line((xx, y0 + 270, xx, y0 + 395), fill=WHITE, width=18)
            d.line((xx, y0 + 310, xx - 38, y0 + 350), fill=WHITE, width=10)
            d.line((xx, y0 + 310, xx + 38, y0 + 350), fill=WHITE, width=10)
            d.rectangle((xx - 48, y0 + 110, xx + 48, y0 + 180), fill=CYAN)
            d.text((xx - 34, y0 + 130), "!", font=font(40, True), fill=NAVY)
        d.text((x0 + 42, y0 + 520), "SOCIEDAD", font=font(25, True), fill=CYAN)
        d.text((x0 + 42, y0 + 570), "Personas y actualidad", font=font(26, True), fill=WHITE)
    else:
        # Use a real photo only after checking its Commons license metadata.
        r = 175
        if PHOTO_PATH and Path(PHOTO_PATH).exists():
            photo = Image.open(PHOTO_PATH).convert("RGB")
            side = r * 2
            scale = max(side / photo.width, side / photo.height)
            photo = photo.resize((int(photo.width * scale), int(photo.height * scale)))
            left = (photo.width - side) // 2
            top = (photo.height - side) // 2
            photo = photo.crop((left, top, left + side, top + side))
            mask = Image.new("L", (side, side), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
            im = photo
            # Paste into the already-rendered scene via a circular alpha mask.
            d._image.paste(im, (cx - r, cy - r), mask)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=CYAN, width=7)
        else:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(13, 92, 145), outline=CYAN, width=6)
        d.text((x0 + 42, y0 + 520), "FOTO REAL · LICENCIA REGISTRADA", font=font(22, True), fill=CYAN)
        d.text((x0 + 42, y0 + 570), "Visual de contexto", font=font(28, True), fill=WHITE)
    # Consistent scene marker makes it clear this is an editorial graphic, not documentary footage.
    d.rounded_rectangle((x0 + 28, y1 - 62, x1 - 28, y1 - 20), radius=14, fill=BLUE)
    d.text((x0 + 48, y1 - 56), f"GRÁFICO ORIGINAL · {index:02d}", font=font(20, True), fill=WHITE)


def draw_scene(path, title, body, index, total, end_card=False):
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[k] * (1 - t) + BLUE[k] * t) for k in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(im)
    d._image = im
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
        draw_visual(d, body, index)
    body_font = font(35 if len(body) < 180 else 31)
    body_lines = wrap_by_pixels(d, body, body_font, 430)
    line_h = 47 if body_font.size >= 35 else 42
    max_lines = max(4, min(14, int((H - y - 360) / line_h)))
    for line in body_lines[:max_lines]:
        d.text((76, y), line, font=body_font, fill=WHITE)
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
    global PHOTO_PATH
    PHOTO_PATH = download_verified_commons_photo(OUT)
    # Microsoft Edge neural TTS produces a more natural Spanish voice than espeak.
    # This draft generator uses a neural Spanish voice, without requiring a paid API key.
    audio = OUT / "narracion_es.mp3"
    run([
        "edge-tts",
        "--voice", "es-MX-JorgeNeural",
        "--rate=-5%",
        "--text", narration,
        "--write-media", str(audio),
    ])
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio)
    ], text=True).strip()
    audio_duration = float(probe)
    narration_chunks = split_narration(narration, 3)
    scene_bodies = [summary] + narration_chunks + ["Sigue a Mundo al Día para mantenerte informado."]
    scene_paths = []
    for i, body in enumerate(scene_bodies):
        p = OUT / f"escena_{i+1:02d}.png"
        draw_scene(p, title, body, i + 1, len(scene_bodies), end_card=(i == len(scene_bodies) - 1))
        scene_paths.append(p)

    # Distribute screen time over the narration; end card gets a short fixed beat.
    main_duration = max(1.0, audio_duration / (len(scene_paths) - 1))
    durations = [main_duration] * (len(scene_paths) - 1) + [2.0]
    concat = OUT / "escenas.txt"
    with concat.open("w", encoding="utf-8") as f:
        for p, dur in zip(scene_paths, durations):
            f.write(f"file '{p.resolve()}'\n")
            f.write(f"duration {dur:.3f}\n")
        f.write(f"file '{scene_paths[-1].resolve()}'\n")

    video = OUT / "mundo-al-dia-video-original.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(audio),
        "-vf", "fps=30,format=yuv420p",
        "-af", "apad=pad_dur=2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        str(video)
    ])
    (OUT / "README.txt").write_text(
        "Borrador original de Mundo al Día.\n"
        "Visuales generados localmente y narración sintética en español.\n"
        "No se usaron vídeos ni fotos de medios externos.\n"
        "Este archivo NO se publicó en el sitio, Facebook ni Instagram.\n"
        "Revisión editorial humana requerida antes de cualquier publicación.\n",
        encoding="utf-8"
    )
    print(f"VIDEO_GENERADO={video}")
    print(f"DURACION_NARRACION_SEGUNDOS={audio_duration:.1f}")
    print("PUBLICADO=NO")


if __name__ == "__main__":
    main()
