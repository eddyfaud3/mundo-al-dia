#!/usr/bin/env python3
"""Create a Mundo al Día video draft from a recent direct publisher RSS item."""
import html
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = [
    "https://rss.dw.com/rdf/rss-sp-all",
    "https://feeds.bbci.co.uk/mundo/rss.xml",
    "https://www.france24.com/es/rss",
]

def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def tag_text(node, names):
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    candidates = []
    for feed_url in FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "MundoAlDiaVideoBot/1.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read(3_000_000)
            root = ET.fromstring(data)
            for item in root.findall(".//item"):
                title = clean(tag_text(item, ["title"]))
                link = clean(tag_text(item, ["link"]))
                description = clean(tag_text(item, ["description", "{http://purl.org/rss/1.0/modules/content/}encoded"]))
                date_text = tag_text(item, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
                if not title or len(title) < 18 or not link.startswith("https://") or len(description) < 60:
                    continue
                try:
                    date = parsedate_to_datetime(date_text) if date_text else datetime.now(timezone.utc)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    date = date.astimezone(timezone.utc)
                except Exception:
                    date = datetime.now(timezone.utc)
                if date < cutoff:
                    continue
                candidates.append((date, title, link, description))
        except Exception as exc:
            print(f"Feed no disponible {feed_url}: {exc}", file=sys.stderr)
    candidates.sort(reverse=True, key=lambda item: item[0])
    if not candidates:
        raise SystemExit("No hay noticias recientes con texto suficiente; no se crea un vídeo.")
    last_error = None
    for date, title, link, description in candidates[:12]:
        title = title[:175].strip()
        summary = description[:1000].strip()
        if len(summary) < 60:
            continue
        narration = (
            "Última hora. " + title + ". " + summary +
            " Seguiremos atentos a las actualizaciones publicadas por la fuente original. "
            "Consulta la información de origen para conocer nuevos detalles. Mundo al Día. El mundo, al día."
        )
        narration = re.sub(r"\s+", " ", narration).strip()
        if len(narration) > 2500:
            narration = narration[:2490].rsplit(" ", 1)[0] + "."
        print(f"Probando noticia: {title}", file=sys.stderr)
        result = subprocess.run([
            sys.executable, "scripts/create_video_draft.py",
            "--title", title,
            "--summary", summary,
            "--narration", narration,
            "--source-url", link,
        ])
        if result.returncode == 0:
            print(f"BORRADOR_CREADO={title}", file=sys.stderr)
            return
        last_error = f"No se pudo generar vídeo con {link}"
        print(f"Se prueba la siguiente noticia. {last_error}", file=sys.stderr)
    raise SystemExit(last_error or "No se pudo crear un vídeo con imágenes de la fuente original.")

if __name__ == "__main__":
    main()
