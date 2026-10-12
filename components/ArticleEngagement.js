"use client";

import { useEffect, useState } from "react";

function getClientKey() {
  let key = localStorage.getItem("mundo-al-dia-client-key");
  if (!key) {
    key = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, "")
      : Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("mundo-al-dia-client-key", key);
  }
  return key;
}

export default function ArticleEngagement({ slug, title }) {
  const [views, setViews] = useState(0);
  const [likes, setLikes] = useState(0);
  const [liked, setLiked] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    const likedKey = "mundo-al-dia-liked-" + slug;
    setLiked(localStorage.getItem(likedKey) === "yes");

    fetch("/api/articles/" + encodeURIComponent(slug) + "/engagement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "view" }),
      cache: "no-store"
    })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (active && data) {
          setViews(Number(data.view_count) || 0);
          setLikes(Number(data.like_count) || 0);
        }
      })
      .finally(() => { if (active) setReady(true); });

    return () => { active = false; };
  }, [slug]);

  async function handleLike() {
    if (liked) return;
    try {
      const response = await fetch("/api/articles/" + encodeURIComponent(slug) + "/engagement", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "like", clientKey: getClientKey() })
      });
      if (!response.ok) return;
      const data = await response.json();
      localStorage.setItem("mundo-al-dia-liked-" + slug, "yes");
      setLiked(true);
      setLikes(Number(data.like_count) || likes + 1);
      setViews(Number(data.view_count) || views);
    } catch {
      // Keep the button available if the connection fails.
    }
  }

  const pageUrl = typeof window !== "undefined" ? window.location.href : "";
  const encodedUrl = encodeURIComponent(pageUrl);
  const encodedTitle = encodeURIComponent(title || "Mundo al Día");

  return (
    <section className="article-engagement" aria-label="Interacciones de la noticia">
      <div className="engagement-stats">
        <span aria-live="polite">👁️ {ready ? views.toLocaleString("es-ES") : "—"} visualizaciones</span>
        <span aria-live="polite">👍 {likes.toLocaleString("es-ES")} Me gusta</span>
      </div>
      <div className="engagement-actions">
        <button type="button" onClick={handleLike} disabled={liked} className={liked ? "engagement-like is-liked" : "engagement-like"}>
          {liked ? "👍 Te gusta" : "👍 Me gusta"}
        </button>
        <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`} target="_blank" rel="noreferrer" className="engagement-share">
          Compartir en Facebook
        </a>
        <a href={`https://api.whatsapp.com/send?text=${encodedTitle}%20${encodedUrl}`} target="_blank" rel="noreferrer" className="engagement-share">
          Compartir por WhatsApp
        </a>
      </div>
      <p className="engagement-note">¿Te importa esta noticia? Dale Me gusta y compártela.</p>
    </section>
  );
}
