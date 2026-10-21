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
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
OUT = Path("video-draft-output")
NAVY = (8, 22, 48)
BLUE = (18, 74, 130)
CYAN = (43, 198, 220)
WHITE = (248, 250, 252)
MUTED = (202, 218, 234)


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

    body_font = font(42 if len(body) < 180 else 36)
    body_lines = wrap_by_pixels(d, body, body_font, 910)
    line_h = 58 if body_font.size >= 42 else 50
    max_lines = max(4, min(11, int((H - y - 300) / line_h)))
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
