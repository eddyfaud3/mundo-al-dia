#!/usr/bin/env python3
"""Create an ORIGINAL Mundo al Día vertical video draft from editor-verified Spanish text.
Uses images extracted from the exact source article for draft review; reuse rights must be verified separately.
Uses a local Spanish neural TTS voice. No publication side effects.
"""
import argparse
import os
import re
import subprocess
import textwrap
import json
import hashlib
from html.parser import HTMLParser
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


class ArticleImageParser(HTMLParser):
    """Collect editorial images declared by the article page, prioritizing its social preview."""
    def __init__(self):
        super().__init__()
        self.images = []
        self.in_article = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article":
            self.in_article += 1
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
                self.images.append((attrs.get("content", ""), True))
        elif tag == "img":
            src = attrs.get("src") or attrs.get("data-src") or attrs.get("data-original") or ""
            srcset = attrs.get("srcset") or attrs.get("data-srcset") or ""
            candidates = []
            if src:
                candidates.append(src)
            for item in srcset.split(","):
                url = item.strip().split(" ")[0] if item.strip() else ""
                if url:
                    candidates.append(url)
            for candidate in candidates:
                self.images.append((candidate, bool(self.in_article)))

    def handle_endtag(self, tag):
        if tag == "article" and self.in_article:
            self.in_article -= 1


def download_article_images(out_dir, article_url, max_images=6):
    """Download images embedded in the exact source article for an unpublished draft.
    This does not grant reuse rights; the manifest clearly flags that editorial rights review is required.
    """
    parsed = urllib.parse.urlparse(article_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("La fuente debe ser una URL HTTPS válida del artículo original.")
    req = urllib.request.Request(article_url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MundoAlDiaDraftGenerator/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            raise RuntimeError("La URL de la fuente no devolvió una página HTML de artículo.")
        html = response.read(5_000_000).decode("utf-8", errors="replace")
    parser = ArticleImageParser()
    parser.feed(html)

    candidates = []
    seen = set()
    for raw_url, preferred in parser.images:
        if not raw_url:
            continue
        url = urllib.parse.urljoin(final_url, raw_url.strip())
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("https", "http") or not p.netloc:
            continue
        lower = url.lower()
        if any(word in lower for word in ("logo", "avatar", "icon", "favicon", "sprite", "tracking", "pixel", "placeholder", "blank.gif")):
            continue
        if url in seen:
            continue
        seen.add(url)
        candidates.append((url, preferred))
    candidates.sort(key=lambda item: not item[1])

    credits = []
    for url, _preferred in candidates:
        if len(credits) >= max_images:
            break
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; MundoAlDiaDraftGenerator/1.0)",
                "Referer": final_url,
            })
            with urllib.request.urlopen(req, timeout=25) as response:
                mime = (response.headers.get("Content-Type") or "").lower()
                raw = response.read(12_000_000)
            if not mime.startswith("image/"):
                continue
            suffix = ".jpg"
            if "png" in mime:
                suffix = ".png"
            elif "webp" in mime:
                suffix = ".webp"
            elif "gif" in mime:
                suffix = ".gif"
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            path = out_dir / f"foto_fuente_{digest}{suffix}"
            path.write_bytes(raw)
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    width, height = image.size
                if width < 500 or height < 280:
                    path.unlink(missing_ok=True)
                    continue
            except Exception:
                path.unlink(missing_ok=True)
                continue
            credits.append({
                "path": path,
                "file": url,
                "source": url,
                "article": final_url,
                "license": "No verificada automáticamente; requiere autorización/licencia antes de publicar",
                "credit": "Consultar crédito indicado en el artículo original",
                "search": "Imagen extraída de la misma página de noticia",
            })
        except Exception:
            continue
    if not credits:
        raise RuntimeError(
            "No se pudieron extraer imágenes editoriales de la página original. "
            "No se usarán fotos de otra fuente para evitar imágenes que no correspondan."
        )
    return credits

def save_photo_credits(out_dir, credits):
    lines = [
        "IMÁGENES DEL ARTÍCULO ORIGINAL — borrador no publicado.",
        "Las imágenes se extrajeron de la misma página de noticia para mejorar la pertinencia.",
        "IMPORTANTE: extraer una imagen no concede derechos de reutilización. Verificar licencia/permisos antes de publicar.",
        "",
    ]
    for i, item in enumerate(credits, 1):
        lines.extend([
            f"Imagen {i}: {item['search']}",
            f"URL de imagen: {item['file']}",
            f"Artículo fuente: {item.get('article', item['source'])}",
            f"Fuente de imagen: {item['source']}",
            f"Licencia/permiso: {item['license']}",
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
    # Usar el logo oficial del repositorio, conservando sus colores azul, rojo, blanco y dorado.
    logo_path = OUT / "logo-mundo-al-dia.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((390, 143), Image.Resampling.LANCZOS)
        plate = Image.new("RGBA", (430, 155), (5, 17, 37, 235))
        plate.alpha_composite(logo, ((430 - logo.width) // 2, (155 - logo.height) // 2))
        im.paste(plate, (54, 42), plate)
        d = ImageDraw.Draw(im)
    d.text((72, 190), "NOTICIAS INTERNACIONALES", font=font(25, True), fill=MUTED)
    if end_card:
        d.text((72, 230), "GRACIAS POR INFORMARTE", font=font(34, True), fill=MUTED)
        d.text((72, 300), "MUNDO AL DÍA", font=font(62, True), fill=WHITE)
        y = 400
    else:
        title_lines = wrap_by_pixels(d, title, font(52, True), 920)
        y = 270
        for line in title_lines[:4]:
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
    ap.add_argument("--source-url", required=True, help="URL HTTPS del artículo original que contiene las imágenes")
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
    # Renderizar el logo SVG oficial para integrarlo nítidamente en el vídeo.
    logo_svg = Path("public/logo-mundo-al-dia.svg")
    if not logo_svg.is_file():
        raise RuntimeError("No se encuentra el logo oficial public/logo-mundo-al-dia.svg.")
    import cairosvg
    cairosvg.svg2png(url=str(logo_svg), write_to=str(OUT / "logo-mundo-al-dia.png"),
                     output_width=900, output_height=330)
    global PHOTO_PATHS, PHOTO_CREDITS
    # Use only images found on the exact article page. Never silently substitute unrelated stock/context images.
    PHOTO_CREDITS = download_article_images(OUT, args.source_url, max_images=6)
    PHOTO_PATHS = [item["path"] for item in PHOTO_CREDITS]
    save_photo_credits(OUT, PHOTO_CREDITS)
    voice = os.environ.get("MUNDO_AL_DIA_TTS_VOICE", "es-MX-JorgeNeural")
    rate = os.environ.get("MUNDO_AL_DIA_TTS_RATE", "-8%")
    # Create one scene per available source-article image (up to six), plus the branded end card.
    # If the article has only one usable image, make one editorial scene instead of forcing three images.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()]
    scene_count = max(1, len(PHOTO_PATHS))
    groups = [[] for _ in range(scene_count)]
    if len(sentences) < scene_count:
        words = narration.split()
        for i in range(scene_count):
            start = round(i * len(words) / scene_count)
            end = round((i + 1) * len(words) / scene_count)
            if start < end:
                groups[i].append(" ".join(words[start:end]))
    else:
        for i, sentence in enumerate(sentences):
            groups[min(scene_count - 1, int(i * scene_count / len(sentences)))].append(sentence)
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
    # Render each still as a gently animated clip (slow Ken Burns zoom), then join clips to narration.
    concat = OUT / "escenas_animadas.txt"
    animated_clips = []
    clip_durations = durations + [2.0]
    for i, (p, dur) in enumerate(zip(scene_paths, clip_durations), 1):
        clip = OUT / f"clip_animado_{i:02d}.mp4"
        frames = max(1, int(round(dur * 30)))
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(p),
            "-vf", "zoompan=z='min(1.0+0.0011*on,1.08)':x='iw/2-(iw/zoom/2)+12*sin(on/35)':y='ih/2-(ih/zoom/2)+10*cos(on/42)':d=1:s=1080x1920:fps=30,format=yuv420p",
            "-frames:v", str(frames), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", str(clip)
        ])
        animated_clips.append(clip)
    with concat.open("w", encoding="utf-8") as f:
        for clip in animated_clips:
            f.write(f"file '{clip.resolve()}'\n")
    video = OUT / "mundo-al-dia-video-original.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(audio),
        "-af", "apad=pad_dur=2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-t", f"{sum(durations)+2:.3f}",
        "-movflags", "+faststart", str(video)
    ])
    (OUT / "video-metadata.json").write_text(
        json.dumps({
            "title": title,
            "caption": args.summary.strip(),
            "source_url": args.source_url,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    (OUT / "README.txt").write_text(
        "Borrador original de Mundo al Día.\n"
        f"Voz neural usada: {voice}; velocidad: {rate}; tono: -2 Hz.\n"
        f"Artículo original: {args.source_url}\n"
        "Las imágenes provienen de la página del artículo; sus derechos NO están verificados automáticamente.\n"
        "Revisar FUENTE_Y_LICENCIA_FOTO.txt y confirmar pertinencia visual y permisos antes de publicar.\n"
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
