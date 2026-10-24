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
    """Create the reference-style vertical news card with a real article image and readable summary."""
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[k] * (1 - t) + BLUE[k] * t) for k in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 20), fill=CYAN)
    d.ellipse((790, -190, 1280, 300), outline=(35, 112, 165), width=5)
    d.ellipse((-220, 1510, 220, 1950), outline=(35, 112, 165), width=5)

    logo_path = OUT / "logo-mundo-al-dia.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((390, 143), Image.Resampling.LANCZOS)
        plate = Image.new("RGBA", (430, 155), (5, 17, 37, 235))
        plate.alpha_composite(logo, ((430 - logo.width) // 2, (155 - logo.height) // 2))
        im.paste(plate, (54, 42), plate)
        d = ImageDraw.Draw(im)

    d.text((72, 225), "NOTICIAS INTERNACIONALES", font=font(23, True), fill=CYAN)
    title_font = font(45, True)
    title_lines = wrap_by_pixels(d, title, title_font, 930)
    while len(title_lines) > 3 and title_font.size > 32:
        title_font = font(title_font.size - 2, True)
        title_lines = wrap_by_pixels(d, title, title_font, 930)
    if len(title_lines) > 3:
        title_lines = title_lines[:3]
        last = title_lines[-1]
        while last and d.textbbox((0, 0), last + "…", font=title_font)[2] > 930:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        title_lines[-1] = last.rstrip(" ,;:") + "…"
    y = 275
    for line in title_lines:
        d.text((72, y), line, font=title_font, fill=WHITE)
        y += title_font.size + 16
    d.rounded_rectangle((72, y + 5, 235, y + 16), radius=5, fill=CYAN)

    # Use only the image extracted from this exact article page. Rights remain a separate manual check.
    if not PHOTO_PATHS:
        raise RuntimeError("No se encontró una foto del artículo original; se detiene el vídeo.")
    photo_path = Path(PHOTO_PATHS[0])
    if not photo_path.is_file():
        raise RuntimeError("No está disponible la foto extraída del artículo original.")
    photo = Image.open(photo_path).convert("RGB")
    x0, y0, x1, y1 = 72, max(470, y + 55), 1008, max(940, y + 525)
    target_w, target_h = x1 - x0, y1 - y0
    scale = max(target_w / photo.width, target_h / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.Resampling.LANCZOS)
    left = (photo.width - target_w) // 2
    top = (photo.height - target_h) // 2
    im.paste(photo.crop((left, top, left + target_w, top + target_h)), (x0, y0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x1, y1), radius=18, outline=CYAN, width=5)

    summary = re.sub(r"\s+", " ", body.strip())
    if not summary:
        raise RuntimeError("Falta el resumen editorial para mostrar debajo de la fotografía.")
    summary_top = y1 + 52
    summary_font = font(30, False)
    lines = wrap_by_pixels(d, summary, summary_font, 840)
    line_h = 43
    # Never silently cut a sentence: shrink the type until the complete card fits.
    while len(lines) * line_h > (1745 - summary_top - 72) and summary_font.size > 22:
        summary_font = font(summary_font.size - 2, False)
        lines = wrap_by_pixels(d, summary, summary_font, 840)
    if len(lines) * line_h > (1745 - summary_top - 72):
        raise RuntimeError("El texto completo no cabe en la tarjeta; se detiene para evitar frases cortadas.")
    panel_bottom = summary_top + 58 + len(lines) * line_h
    d.rounded_rectangle((72, summary_top - 20, 1008, panel_bottom), radius=22,
                        fill=(5, 24, 53), outline=(43, 198, 220), width=2)
    yy = summary_top + 8
    for line in lines:
        d.text((112, yy), line, font=summary_font, fill=WHITE)
        yy += line_h

    footer_y = 1815
    d.line((72, footer_y - 28, 1008, footer_y - 28), fill=CYAN, width=3)
    d.text((72, footer_y), "INFORMACIÓN EN ESPAÑOL · MUNDO AL DÍA",
           font=font(21, True), fill=MUTED)
    d.text((1008, footer_y), f"{index:02d}", font=font(22, True), fill=CYAN, anchor="ra")
    im.save(path, quality=95)

def fit_narration_to_30_seconds(text, max_words=32):
    """Keep a short Spanish narration with room for a 30-second video."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chosen = []
    for sentence in sentences:
        candidate = " ".join(chosen + [sentence]).strip()
        if len(candidate.split()) <= max_words:
            chosen.append(sentence)
        else:
            break
    if chosen:
        return " ".join(chosen)
    words = cleaned.split()[:max_words]
    if words:
        return " ".join(words).rstrip(",;:") + "."
    return "Información en desarrollo."


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


def split_summary_cards(text, count=3):
    """Split on real sentence boundaries so no card ends halfway through a sentence."""
    clean = re.sub(r"\s+", " ", text.strip())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    if len(sentences) >= count:
        # Keep complete sentences together, distributing them as evenly as possible.
        groups = [[] for _ in range(count)]
        for i, sentence in enumerate(sentences):
            groups[min(count - 1, i * count // len(sentences))].append(sentence)
        cards = [" ".join(group) for group in groups]
    else:
        # If the editor supplied fewer sentences, divide only at word boundaries.
        words = clean.split()
        cards = [" ".join(words[round(i * len(words) / count):round((i + 1) * len(words) / count)]) for i in range(count)]
    return [card for card in cards if card]


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
    PHOTO_PATHS = [str(item["path"]) for item in PHOTO_CREDITS]
    save_photo_credits(OUT, PHOTO_CREDITS)

    summary = re.sub(r"\s+", " ", args.summary.strip())
    if not summary:
        raise RuntimeError("El resumen verificado es obligatorio para el diseño del vídeo.")
    video = OUT / "mundo-al-dia-video-original.mp4"
    narration = re.sub(r"\\s+", " ", summary).strip()
    if not narration:
        raise RuntimeError("La narración debe ser exactamente el mismo texto que aparece debajo de la fotografía.")
    if not narration:
        raise RuntimeError("No hay narración en español; no se generará un vídeo silencioso.")
    # Rotate between male/female Spanish neural voices, consistently per story.
    voices = ["es-MX-JorgeNeural", "es-MX-DaliaNeural", "es-ES-AlvaroNeural", "es-ES-ElviraNeural"]
    voice_index = int(hashlib.sha256((title + args.source_url).encode("utf-8")).hexdigest()[:8], 16) % len(voices)
    selected_voice = voices[voice_index]
    narration_audio = OUT / ("narracion-" + selected_voice + ".mp3")
    # No subtitles: these are editorial story panels, not synchronized captions.
    run(["edge-tts", "--voice", selected_voice, "--rate=+8%", "--text", narration,
         "--write-media", str(narration_audio)])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(narration_audio)],
        check=True, capture_output=True, text=True
    )
    audio_seconds = float(probe.stdout.strip())
    if audio_seconds > 120:
        raise RuntimeError(f"La narración es demasiado larga ({audio_seconds:.1f}s); máximo permitido: 120 segundos.")
    scene_seconds = max(6.0, (audio_seconds + 1.5) / 3.0)
    scene_frames = int(scene_seconds * 30)
    # Three different editorial panels use text extracted from this news summary.
    cards = split_summary_cards(summary, 3)
    labels = ["LO ESENCIAL", "QUÉ SE SABE", "LO QUE SIGUE"]
    segment_paths = []
    for idx, (card_text, label) in enumerate(zip(cards, labels), 1):
        still = OUT / f"escena_noticia_{idx}.png"
        draw_scene(still, title, label + ": " + card_text, index=idx)
        segment = OUT / f"segmento_{idx}.mp4"
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(still),
            "-vf", "zoompan=z='min(1.0+0.00008*on,1.06)':x='max(0,min(iw-iw/zoom,(iw-iw/zoom)/2+9*sin(on/55)))':y='max(0,min(ih-ih/zoom,(ih-ih/zoom)/2+9*cos(on/67)))':d=1:s=1080x1920:fps=30,format=yuv420p",
            "-frames:v", "300", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-pix_fmt", "yuv420p", "-t", "10", "-movflags", "+faststart", str(segment)
        ])
        segment_paths.append(segment)
    concat_list = OUT / "segmentos.txt"
    concat_list.write_text("".join("file '" + p.resolve().as_posix() + "'\n" for p in segment_paths), encoding="utf-8")
    silent_video = OUT / "video-sin-audio.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
         "-safe", "0", "-i", str(concat_list), "-c", "copy", str(silent_video)])
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(silent_video), "-i", str(narration_audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-af", "apad", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-t", "30", "-movflags", "+faststart", str(video)
    ])

    (OUT / "video-metadata.json").write_text(
        json.dumps({"title": title, "source_url": args.source_url,
                    "duration_seconds": round(scene_seconds * 3, 2), "narration_duration_seconds": round(audio_seconds, 2), "narration_text_matches_overlay": True, "overlay_text": "three_story_specific_editorial_cards",
                    "photo": "one image extracted from the exact source article; rights require manual clearance", "visual": "branded news layout with headline, article photo, on-screen summary and subtle Ken Burns motion",
                    "voice": selected_voice, "voice_rotation": voices, "audio": "Spanish narration",
                    "captions": "none; Spanish narration only"}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
    )
    (OUT / "README.txt").write_text(
        "Borrador de vídeo Mundo al Día: diseño vertical con logotipo, titular, fotografía del artículo y resumen visible.\\n"
        "Incluye narración en español (voz es-MX-JorgeNeural), sin subtítulos.\\n"
        f"Artículo original: {args.source_url}\\n"
        "IMPORTANTE: la foto se extrajo de la página del artículo, pero sus derechos/licencia deben verificarse antes de publicar.\\n"
        "Este archivo NO se publicó en la web, Facebook ni Instagram.\\n",
        encoding="utf-8"
    )
    print(f"VIDEO_GENERADO={video}")
    print(f"DURACION_VIDEO_SEGUNDOS={scene_seconds * 3:.2f}")
    print(f"VOZ={selected_voice}")
    print(f"DURACION_NARRACION_SEGUNDOS={audio_seconds:.2f}")
    print("SUBTITULOS=NO")
    print("FOTO=EXTRAIDA_DEL_ARTICULO_ORIGINAL; DERECHOS_PENDIENTES_DE_REVISION")
    print("PUBLICADO=NO")


if __name__ == "__main__":
    main()
