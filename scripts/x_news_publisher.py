#!/usr/bin/env python3
"""Mundo al Día — isolated, conservative X news publisher."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    ("DW Español", "https://rss.dw.com/rdf/rss-sp-all"),
    ("BBC News Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("France 24 Español", "https://www.france24.com/es/rss"),
]
MAX_AGE_HOURS = 18
MIN_SOURCE_COUNT = 2
MIN_TITLE_OVERLAP = 0.30
OUT = "x-draft.json"
STOPWORDS = {
    "para", "desde", "sobre", "tras", "ante", "entre", "como", "pero", "porque",
    "cuando", "donde", "este", "esta", "estos", "estas", "unos", "unas", "una",
    "uno", "por", "con", "sin", "del", "las", "los", "que", "una", "the", "and",
    "with", "after", "over", "into", "from", "says", "said", "latest", "video",
}


def http(url, headers=None, data=None, method=None, timeout=25):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = (value.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"\s+", " ", value).strip()


def title_tokens(title):
    words = re.findall(r"[a-záéíóúüñ0-9]{3,}", (title or "").lower())
    return {word for word in words if word not in STOPWORDS}


def title_overlap(left, right):
    a, b = title_tokens(left), title_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def corroborated_items(items):
    """Keep only stories whose titles match across at least two distinct outlets."""
    qualified = []
    for item in items:
        matches = {
            other["source"] for other in items
            if other["source"] != item["source"]
            and title_overlap(item["title"], other["title"]) >= MIN_TITLE_OVERLAP
        }
        if len(matches) >= MIN_SOURCE_COUNT - 1:
            copy = dict(item)
            copy["corroborating_sources"] = sorted(matches | {item["source"]})
            qualified.append(copy)
    return sorted(qualified, key=lambda x: x["published"], reverse=True)


def rss_items():
    found = []
    now = datetime.now(timezone.utc)
    for source, url in FEEDS:
        try:
            _, raw = http(url, {"User-Agent": "MundoAlDiaNews/1.0"})
            root = ET.fromstring(raw)
            for item in root.findall(".//item"):
                title = clean(item.findtext("title"))
                link = (item.findtext("link") or "").strip()
                desc = clean(item.findtext("description"))
                date_text = item.findtext("pubDate") or ""
                try:
                    published = parsedate_to_datetime(date_text).astimezone(timezone.utc)
                except Exception:
                    continue
                age = (now - published).total_seconds() / 3600
                if title and len(desc) >= 50 and link.startswith("https://") and 0 <= age <= MAX_AGE_HOURS:
                    found.append({
                        "source": source, "title": title, "description": desc,
                        "url": link, "published": published.isoformat(),
                        "age_hours": round(age, 1),
                    })
        except Exception as exc:
            print(f"WARNING: Feed {source} inaccessible: {exc}", file=sys.stderr)
    return sorted(found, key=lambda x: x["published"], reverse=True)


def x_recent_urls(token):
    headers = {"Authorization": f"Bearer {token}"}
    _, me_raw = http("https://api.x.com/2/users/me", headers)
    me = json.loads(me_raw)
    user_id = me["data"]["id"]
    query = urllib.parse.urlencode({"max_results": "20", "tweet.fields": "text"})
    _, posts_raw = http(f"https://api.x.com/2/users/{user_id}/tweets?{query}", headers)
    posts = json.loads(posts_raw).get("data", [])
    return [p.get("text", "") for p in posts]


def make_post(item, api_key):
    source_context = (
        f"Medios que coinciden en el tema: {', '.join(item['corroborating_sources'])}\n"
        f"Medio de la nota enlazada: {item['source']}\nTitular: {item['title']}\n"
        f"Descripción RSS: {item['description']}\nEnlace original: {item['url']}"
    )
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": (
                "Eres editor de Mundo al Día. Redacta UN post periodístico en español, "
                "claro, neutral y atractivo, máximo 220 caracteres SIN contar el enlace. "
                "Usa únicamente los datos de la nota enlazada; los otros medios solo "
                "corroboran que el tema está siendo cubierto. No inventes detalles, cifras, "
                "citas ni consecuencias. No uses 'ÚLTIMA HORA' salvo que se justifique. "
                "Devuelve únicamente el texto del post, sin comillas ni URL."
            )},
            {"role": "user", "content": source_context},
        ],
        "temperature": 0.2,
    }
    _, raw = http(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json.dumps(payload).encode("utf-8"), "POST"
    )
    text = json.loads(raw)["choices"][0]["message"]["content"].strip().strip('"')
    if not text:
        raise SystemExit("OpenAI devolvió un borrador vacío; no se publica.")
    return f"{text}\n{item['url']}"


def main():
    token = os.getenv("X_USER_ACCESS_TOKEN", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    publish_enabled = (
        os.getenv("X_AUTO_PUBLISH_ENABLED", "false").lower() == "true"
        or os.getenv("X_PUBLISH_REQUESTED", "false").lower() == "true"
    )
    if not openai_key:
        raise SystemExit("Falta OPENAI_API_KEY; no se genera ni publica un borrador.")
    if publish_enabled and not token:
        raise SystemExit("Publicación bloqueada: falta X_USER_ACCESS_TOKEN.")

    qualified = corroborated_items(rss_items())
    if not qualified:
        raise SystemExit(
            "No hay una noticia reciente corroborada por al menos dos medios distintos; "
            "no se genera ni publica nada."
        )

    recent_texts = x_recent_urls(token) if publish_enabled else []
    selected = next(
        (item for item in qualified
         if not any(item["url"] in post for post in recent_texts)),
        None,
    )
    if selected is None:
        raise SystemExit("Las noticias corroboradas ya aparecen en los últimos posts; no se repite.")

    post_text = make_post(selected, openai_key)
    if len(post_text) > 280:
        link = "\n" + selected["url"]
        body = post_text[:-len(link)]
        post_text = body[:max(0, 279 - len(link))].rstrip() + link
    if len(post_text) > 280:
        raise SystemExit("El post supera el límite de X; no se publica.")

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "published" if publish_enabled else "draft",
        "source": selected["source"],
        "corroborating_sources": selected["corroborating_sources"],
        "title": selected["title"],
        "article_url": selected["url"],
        "post_text": post_text,
    }
    if publish_enabled:
        payload = json.dumps({"text": post_text}).encode("utf-8")
        _, raw = http(
            "https://api.x.com/2/tweets",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            payload, "POST"
        )
        response = json.loads(raw)
        result["x_post_id"] = response.get("data", {}).get("id")
        if not result["x_post_id"]:
            raise SystemExit("X no confirmó el ID de la publicación.")
        print(f"Published X post ID: {result['x_post_id']}")
    else:
        print("Draft generated only. X_AUTO_PUBLISH_ENABLED is not true; nothing was posted.")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
