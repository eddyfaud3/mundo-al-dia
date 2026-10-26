#!/usr/bin/env python3
"""Create a video using only the latest published Mundo al Día article."""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

SITE_URL = os.environ.get(
    "MUNDO_AL_DIA_SITE_URL",
    "https://mundo-al-dia-github-production.up.railway.app",
).rstrip("/")

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def main():
    request = urllib.request.Request(
        SITE_URL + "/api/articles",
        headers={"User-Agent": "MundoAlDiaVideoBot/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        articles = json.loads(response.read().decode("utf-8"))

    if not isinstance(articles, list):
        raise SystemExit("La API del sitio no devolvió una lista de noticias.")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=8)
    candidates = []
    for article in articles:
        if not isinstance(article, dict):
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
        except Exception:
            continue
        if published < cutoff or published > now + timedelta(minutes=5):
            continue
        candidates.append((published, article, title, summary))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates:
        raise SystemExit(
            "No hay una noticia publicada recientemente en Mundo al Día con foto HTTPS y texto suficiente. "
            "No se consultarán otras páginas ni fuentes."
        )

    published, article, title, summary = candidates[0]
    summary = summary[:1100].strip()
    article_url = SITE_URL + "/noticia/" + article["slug"]
    narration = (
        "Última hora. " + title + ". " + summary +
        " Esta es la información publicada por Mundo al Día. "
        "Seguiremos atentos a las actualizaciones. Mundo al Día. El mundo, al día."
    )
    narration = re.sub(r"\s+", " ", narration).strip()
    if len(narration) > 2500:
        narration = narration[:2490].rsplit(" ", 1)[0] + "."

    print("NOTICIA_DEL_SITIO=" + title)
    print("ARTICULO=" + article_url)
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
    with open(metadata_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

if __name__ == "__main__":
    main()
