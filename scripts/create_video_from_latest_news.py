#!/usr/bin/env python3
"""Create a video using only the latest published Mundo al Día article."""
import json
import html
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

SITE_URL = os.environ.get(
    "MUNDO_AL_DIA_SITE_URL",
    "https://mundo-al-dia-github-production.up.railway.app",
).rstrip("/")
MAX_ATTEMPTS = 3


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_site_articles():
    url = SITE_URL + "/api/articles"
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MundoAlDiaVideoBot/1.1",
                "Accept": "application/json",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"El sitio respondió HTTP {response.status}.")
                payload = response.read().decode("utf-8")
            articles = json.loads(payload)
            if not isinstance(articles, list):
                raise RuntimeError("La API del sitio no devolvió una lista de noticias.")
            return articles
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as error:
            last_error = error
            print(
                f"Intento {attempt}/{MAX_ATTEMPTS}: no se pudo leer la API de Mundo al Día: {error}",
                file=sys.stderr,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(5 * attempt)
    raise SystemExit(
        "No se pudo conectar con la API de Mundo al Día después de "
        f"{MAX_ATTEMPTS} intentos. No se consultarán fuentes externas. Último error: {last_error}"
    )


def main():
    articles = fetch_site_articles()
    now = datetime.now(timezone.utc)
    # Prefer recent stories, but allow the latest published Mundo al Día article from the last 24 hours.
    # Never recycle older news or consult external sources.
    cutoff = now - timedelta(hours=24)
    candidates = []

    for article in articles:
        if not isinstance(article, dict) or article.get("published") is False:
            continue
        title = clean(article.get("title"))
        slug = clean(article.get("slug"))
        summary = clean(article.get("content") or article.get("excerpt"))
        summary = html.unescape(re.sub(r"<[^>]+>", " ", summary))
        summary = clean(summary)
        image_url = clean(article.get("image_url"))
        created_at = article.get("created_at")
        if not title or not slug or len(summary) < 60 or not image_url.startswith("https://"):
            continue
        try:
            published = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if published < cutoff or published > now + timedelta(minutes=5):
            continue
        candidates.append((published, article, title, summary))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates:
        raise SystemExit(
            "No hay una noticia reciente publicada en Mundo al Día con foto HTTPS y texto suficiente. "
            "No se consultarán otras páginas ni fuentes externas."
        )

    published, article, title, summary = candidates[0]
    # Limpiar créditos editoriales sin borrar los hechos de las noticias.
    def narration_text(value):
        value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
        value = re.sub(r"https?://\S+", " ", value, flags=re.IGNORECASE)
        sentences = re.split(r"(?<=[.!?])\s+", value)
        blocked = re.compile(
            r"(?i)\b(?:fuente|fuentes|consulta la fuente original|"
            r"esta noticia se prepar[oó] a partir de|esta informaci[oó]n fue publicada por|"
            r"cobertura publicada por|para verificar actualizaciones)\b"
        )
        kept = [s.strip() for s in sentences if s.strip() and not blocked.search(s)]
        return re.sub(r"\s+", " ", " ".join(kept)).strip(" .;:-")

    full_summary = narration_text(summary)
    if len(full_summary) < 60:
        raise SystemExit("La noticia no contiene suficiente información limpia para narrarla.")

    # Objetivo: 45–60 segundos. Se limita el resumen a unas 105 palabras.
    words = full_summary.split()
    if len(words) > 105:
        shortened = " ".join(words[:105])
        last_stop = max(shortened.rfind(". "), shortened.rfind("! "), shortened.rfind("? "))
        if last_stop >= 420:
            shortened = shortened[:last_stop + 1]
        else:
            shortened = shortened.rsplit(" ", 1)[0].rstrip(" ,;:") + "."
        full_summary = shortened
    # Publicación social: solo hashtags, sin enlaces ni créditos de fuentes externas.
    caption_summary = "#MundoAlDia #UltimaHora #Noticias #NoticiasInternacionales #Actualidad"
    article_url = SITE_URL + "/noticia/" + urllib.parse.quote(article["slug"], safe="")
    narration = (
        "Última hora. " + title + ". " + full_summary +
        " Seguiremos atentos a cualquier novedad. Mundo al Día."
    )
    narration = re.sub(r"\s+", " ", narration).strip()
    if len(narration.split()) > 130:
        narration = " ".join(narration.split()[:130]).rsplit(" ", 1)[0].rstrip(" ,;:") + "."


    print("NOTICIA_DEL_SITIO=" + title)
    print("ARTICULO=" + article_url)
    print("FOTO_PRINCIPAL=" + image_url if (image_url := clean(article.get("image_url"))) else "FOTO_PRINCIPAL=no_disponible")

    result = subprocess.run([
        sys.executable, "scripts/create_video_draft.py",
        "--title", title[:175],
        "--summary", caption_summary,
        "--narration", narration,
        "--source-url", article_url,
        "--image-url", image_url,
    ])
    if result.returncode:
        raise SystemExit("No se pudo crear el vídeo con la noticia publicada en Mundo al Día.")

    metadata_path = "video-draft-output/video-metadata.json"
    with open(metadata_path, encoding="utf-8") as handle:
        metadata = json.load(handle)
    metadata["article_slug"] = article["slug"]
    metadata["article_published_at"] = published.isoformat()
    metadata["source_policy"] = "Solo artículos publicados en Mundo al Día; sin búsquedas externas."
    metadata["primary_article_image"] = image_url
    with open(metadata_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
