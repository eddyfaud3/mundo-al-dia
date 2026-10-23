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
    # Safer image policy: prefer ONLY the article's social preview (og:image).
    # If there is no social preview, use ONLY the first image found inside an article element.
    # Never fill the video with every image found across the page, as those may be related-story thumbnails.
    preferred = [item for item in candidates if item[1]]
    in_article = [item for item in candidates if item[1] is False]
    candidates = preferred[:1] if preferred else in_article[:1]

    credits = []
    for url, _preferred in candidates:
        if len(credits) >= 1:
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


def draw_scene(path, title, body="", index=1, total=1, end_card=False):
    """Create a clean vertical visual: official logo, headline, and article photo only."""
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

    logo_path = OUT / "logo-mundo-al-dia.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((390, 143), Image.Resampling.LANCZOS)
        plate = Image.new("RGBA", (430, 155), (5, 17, 37, 235))
        plate.alpha_composite(logo, ((430 - logo.width) // 2, (155 - logo.height) // 2))
        im.paste(plate, (54, 42), plate)
        d = ImageDraw.Draw(im)

    title_font = font(52, True)
    title_lines = wrap_by_pixels(d, title, title_font, 920)
    while len(title_lines) > 4 and title_font.size > 36:
        title_font = font(title_font.size - 2, True)
        title_lines = wrap_by_pixels(d, title, title_font, 920)
    y = 245
    line_height = title_font.size + 18
    for line in title_lines[:4]:
        d.text((72, y), line, font=title_font, fill=WHITE)
        y += line_height
    d.rounded_rectangle((72, y + 8, 220, y + 19), radius=5, fill=CYAN)

    # Image is used only in an unpublished draft; its reuse rights still need review.
    x0, y0, x1, y1 = 72, max(600, y + 65), 1008, 1540
    if not PHOTO_PATHS:
        raise RuntimeError("No se encontró imagen del artículo para el borrador.")
    photo = Image.open(PHOTO_PATHS[0]).convert("RGB")
    tw, th = x1 - x0, y1 - y0
    scale = max(tw / photo.width, th / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.Resampling.LANCZOS)
    left = (photo.width - tw) // 2
    top = (photo.height - th) // 2
    im.paste(photo.crop((left, top, left + tw, top + th)), (x0, y0))
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0, x1, y1), outline=WHITE, width=2)
    im.save(path, quality=95)

def caption_phrases(text, max_chars=30):
    """Split narration into short, readable caption cards (max two short lines)."""
    words = re.sub(r"\s+", " ", text.strip()).split()
    phrases, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > max_chars:
            phrases.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        phrases.append(" ".join(current))
    return phrases


def srt_timestamp(seconds):
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def ass_time(seconds):
    centiseconds = max(0, int(round(seconds * 100)))
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def write_timed_subtitles(chunks, durations, output_path):
    """Write explicit ASS styling so captions stay readable below the photo."""
    entries = []
    offset = 0.0
    for chunk, duration in zip(chunks, durations):
        phrases = caption_phrases(chunk, max_chars=28)
        weights = [max(1, len(p.split())) for p in phrases]
        total_weight = sum(weights) or 1
        cursor = offset
        for phrase, weight in zip(phrases, weights):
            segment = duration * weight / total_weight
            start = max(offset, cursor)
            end = max(start + 0.45, cursor + segment - 0.02)
            # ASS override-sensitive characters are escaped before rendering.
            safe_phrase = phrase.replace("\\", r"\\").replace("{", r"\\{").replace("}", r"\\}")
            entries.append((start, end, safe_phrase))
            cursor += segment
        offset += duration

    header = """[Script Info]
Title: Mundo al Día - Subtítulos
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,40,&H00FFFFFF,&H0000FFFF,&H00101828,&HCC081830,-1,0,3,2,0,2,90,90,650,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with output_path.open("w", encoding="utf-8") as f:
        f.write(header)
        for start, end, phrase in entries:
            f.write(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{phrase}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=False, default="")
    ap.add_argument("--narration", required=False, default="")
    ap.add_argument("--source-url", required=True, help="URL HTTPS del artículo original")
    args = ap.parse_args()
    title = args.title.strip()
    if not title or len(title) > 180:
        raise SystemExit("El titular debe tener entre 1 y 180 caracteres.")

    OUT.mkdir(parents=True, exist_ok=True)
    logo_svg = Path("public/logo-mundo-al-dia.svg")
    if not logo_svg.is_file():
        raise RuntimeError("No se encuentra el logo oficial public/logo-mundo-al-dia.svg.")
    import cairosvg
    cairosvg.svg2png(url=str(logo_svg), write_to=str(OUT / "logo-mundo-al-dia.png"),
                     output_width=900, output_height=330)

    global PHOTO_PATHS, PHOTO_CREDITS
    PHOTO_CREDITS = download_article_images(OUT, args.source_url, max_images=1)
    PHOTO_PATHS = [item["path"] for item in PHOTO_CREDITS]
    save_photo_credits(OUT, PHOTO_CREDITS)

    still = OUT / "escena_titulo.png"
    draw_scene(still, title)
    video = OUT / "mundo-al-dia-video-original.mp4"
    narration_audio = OUT / "narracion-es-MX-JorgeNeural.mp3"
    narration = re.sub(r"\s+", " ", (args.narration or args.summary or title).strip())
    if not narration:
        raise RuntimeError("No hay narración en español; no se generará un vídeo silencioso.")
    # Keep the approved Spanish neural voice and ask edge-tts for timed SRT captions.
    subtitles = OUT / "subtitulos-es.srt"
    run(["edge-tts", "--voice", "es-MX-JorgeNeural", "--rate=+12%", "--text", narration,
         "--write-media", str(narration_audio), "--write-subtitles", str(subtitles)])
    if not subtitles.is_file() or subtitles.stat().st_size < 20:
        raise RuntimeError("No se generó un archivo SRT de subtítulos válido; se detiene el borrador.")
    srt_text = subtitles.read_text(encoding="utf-8-sig")
    if "-->" not in srt_text or not re.search(r"\d{2}:\d{2}:\d{2},\d{3}", srt_text):
        raise RuntimeError("El archivo de subtítulos no tiene formato SRT válido; se detiene el borrador.")
    silent_video = OUT / "video-sin-audio.mp4"
    frames = 30 * 30
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(still),
        "-vf", "zoompan=z='min(1.0+0.00004*on,1.035)':x='max(0,min(iw-iw/zoom,(iw-iw/zoom)/2+5*sin(on/55)))':y='max(0,min(ih-ih/zoom,(ih-ih/zoom)/2+5*cos(on/67)))':d=1:s=1080x1920:fps=30,format=yuv420p",
        "-frames:v", str(frames), "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-t", "30", "-movflags", "+faststart", str(silent_video)
    ])
    # Burn the timed Spanish SRT captions into the picture so they remain visible
    # on both Facebook and Instagram, independent of each platform's caption settings.
    # Keep the narration audio and exact 30-second vertical video.
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(silent_video), "-i", str(narration_audio),
        "-vf", f"subtitles={subtitles.as_posix()}:force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101828,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV=150'",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-t", "30", "-movflags", "+faststart", str(video)
    ])

    (OUT / "video-metadata.json").write_text(
        json.dumps({"title": title, "source_url": args.source_url,
                    "duration_seconds": 30, "overlay_text": "title_only",
                    "voice": "es-MX-JorgeNeural", "audio": "Spanish narration",
                    "captions": "Spanish SRT burned into video for Facebook and Instagram"}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
    )
    (OUT / "README.txt").write_text(
        "Borrador de vídeo Mundo al Día: 30 segundos con narración en español (voz es-MX-JorgeNeural) y subtítulos españoles visibles integrados en el vídeo.\\n"
        "En pantalla solo aparecen el logotipo y el titular; no se añaden otros textos.\\n"
        f"Artículo original: {args.source_url}\\n"
        "La licencia de la imagen no se verifica automáticamente. Confirmar permisos antes de publicar.\\n"
        "Este archivo NO se publicó en la web, Facebook ni Instagram.\\n",
        encoding="utf-8"
    )
    print(f"VIDEO_GENERADO={video}")
    print("DURACION_OBJETIVO_SEGUNDOS=30")
    print("VOZ=es-MX-JorgeNeural")
    print("SUBTITULOS=SRT_GENERADO")
    print("PUBLICADO=NO")


if __name__ == "__main__":
    main()
