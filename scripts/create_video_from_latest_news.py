#!/usr/bin/env python3
"""Create a video using only the latest published Mundo al Día article."""
import json
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
    return re.sub(r"\\s+", " ", str(value or "")).strip()


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
    # A 12-hour window tolerates a delayed site run without recycling an old story.
    cutoff = now - timedelta(hours=12)
    candidates = []

    for article in articles:
        if not isinstance(article, dict) or article.get("published") is False:
            continue
        title = clean(article.get("title"))
        slug = clean(article.get("slug"))
        summary = clean(article.get("excerpt") or article.get("content"))
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
    summary = summary[:1100].strip()
    article_url = SITE_URL + "/noticia/" + urllib.parse.quote(article["slug"], safe="")
    narration = (
        "Última hora. " + title + ". " + summary +
        " Esta es la información publicada por Mundo al Día. "
        "Seguiremos atentos a las actualizaciones. Mundo al Día. El mundo, al día."
    )
    narration = re.sub(r"\\s+", " ", narration).strip()
    if len(narration) > 2500:
        narration = narration[:2490].rsplit(" ", 1)[0] + "."

    print("NOTICIA_DEL_SITIO=" + title)
    print("ARTICULO=" + article_url)
    print("FOTO_PRINCIPAL=" + image_url if (image_url := clean(article.get("image_url"))) else "FOTO_PRINCIPAL=no_disponible")

    result = subprocess.run([
        sys.executable, "scripts/create_video_draft.py",
        "--title", title[:175],
        "--summary", summary,
        "--narration", narration,
        "--source-url", article_url,
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
        handle.write("\\n")


if __name__ == "__main__":
    main()
