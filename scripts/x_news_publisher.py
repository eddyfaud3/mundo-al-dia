#!/usr/bin/env python3
"""Mundo al Día — isolated X news publisher.
Reads public RSS feeds, drafts one Spanish post, and publishes only when explicitly enabled.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("DW Español", "https://rss.dw.com/rdf/rss-sp-all"),
    ("BBC News Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("France 24 Español", "https://www.france24.com/es/rss"),
]
MAX_AGE_HOURS = 18
OUT = "x-draft.json"


def http(url, headers=None, data=None, method=None, timeout=25):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = (value.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"\s+", " ", value).strip()


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
                    from email.utils import parsedate_to_datetime
                    published = parsedate_to_datetime(date_text).astimezone(timezone.utc)
                except Exception:
                    continue
                age = (now - published).total_seconds() / 3600
                if title and len(desc) >= 50 and link.startswith("https://") and 0 <= age <= MAX_AGE_HOURS:
                    found.append({"source": source, "title": title, "description": desc,
                                  "url": link, "published": published.isoformat(), "age_hours": round(age, 1)})
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
        f"Medio: {item['source']}\nTitular: {item['title']}\n"
        f"Descripción RSS: {item['description']}\nEnlace original: {item['url']}"
    )
    if not api_key:
        # Draft-only fallback; never publish an AI-free guess automatically.
        return f"{item['title']}\n{item['url']}"
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": (
                "Eres editor de Mundo al Día. Redacta UN post periodístico en español, "
                "claro, neutral y atractivo, máximo 230 caracteres SIN contar el enlace. "
                "Usa solo los datos entregados; no inventes detalles ni afirmes hechos "
                "que no estén respaldados. No uses 'ÚLTIMA HORA' salvo que el texto lo "
                "justifique. Devuelve únicamente el texto del post, sin comillas."
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
    text = json.loads(raw)["choices"][0]["message"]["content"].strip()
    text = text.strip('"')
    return f"{text}\n{item['url']}"


def main():
    items = rss_items()
    if not items:
        raise SystemExit("No hay noticias recientes con descripción suficiente; no se publica.")
    token = os.getenv("X_USER_ACCESS_TOKEN", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    publish_enabled = (os.getenv("X_AUTO_PUBLISH_ENABLED", "false").lower() == "true"\n                      or os.getenv("X_PUBLISH_REQUESTED", "false").lower() == "true")

    recent_texts = []
    if publish_enabled:
        if not token or not openai_key:
            raise SystemExit("Publicación bloqueada: faltan X_USER_ACCESS_TOKEN u OPENAI_API_KEY.")
        recent_texts = x_recent_urls(token)

    selected = None
    for item in items:
        if not any(item["url"] in post for post in recent_texts):
            selected = item
            break
    if selected is None:
        raise SystemExit("Las noticias recientes ya aparecen en las últimas publicaciones; no se repite.")

    post_text = make_post(selected, openai_key)
    if len(post_text) > 280:
        # Keep the source link and trim only generated editorial text.
        link = "\n" + selected["url"]
        body = post_text[:-len(link)]
        post_text = body[:max(0, 279-len(link))].rstrip() + link

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "published" if publish_enabled else "draft",
        "source": selected["source"],
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
        print(f"Published X post ID: {result['x_post_id']}")
    else:
        print("Draft generated only. X_AUTO_PUBLISH_ENABLED is not true; nothing was posted.")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
