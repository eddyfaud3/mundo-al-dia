"use client";

import { useEffect, useState } from "react";

function formatCommentDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function ArticleComments({ slug }) {
  const [comments, setComments] = useState([]);
  const [name, setName] = useState("");
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/articles/" + encodeURIComponent(slug) + "/comments", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (active && data) setComments(Array.isArray(data.comments) ? data.comments : []);
      })
      .catch(() => {
        if (active) setMessage("No se pudieron cargar los comentarios.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [slug]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (sending) return;
    setSending(true);
    setMessage("");

    try {
      const response = await fetch("/api/articles/" + encodeURIComponent(slug) + "/comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, comment }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.error || "No se pudo publicar el comentario.");
        return;
      }
      setComments((current) => [data.comment, ...current].slice(0, 50));
      setName("");
      setComment("");
      setMessage("¡Gracias! Tu comentario se publicó correctamente.");
    } catch {
      setMessage("Error de conexión. Inténtalo de nuevo.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="article-comments" aria-label="Comentarios de la noticia">
      <div className="comments-heading">
        <h2>💬 Comentarios</h2>
        <span>{comments.length} {comments.length === 1 ? "comentario" : "comentarios"}</span>
      </div>
      <p className="comments-intro">¿Qué opinas de esta noticia? Comparte tu opinión con respeto.</p>

      <form className="comments-form" onSubmit={handleSubmit}>
        <label htmlFor="comment-author">Tu nombre</label>
        <input
          id="comment-author"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Escribe tu nombre"
          minLength={2}
          maxLength={50}
          required
        />
        <label htmlFor="comment-message">Tu comentario</label>
        <textarea
          id="comment-message"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="Deja tu comentario aquí..."
          minLength={3}
          maxLength={1000}
          rows={4}
          required
        />
        <div className="comments-form-footer">
          <small>{comment.length}/1000 caracteres</small>
          <button type="submit" disabled={sending}>
            {sending ? "Publicando..." : "Publicar comentario"}
          </button>
        </div>
        <p className="comments-status" aria-live="polite">{message}</p>
      </form>

      <div className="comments-list">
        {loading ? (
          <p className="comments-empty">Cargando comentarios...</p>
        ) : comments.length === 0 ? (
          <p className="comments-empty">Todavía no hay comentarios. ¡Sé la primera persona en comentar!</p>
        ) : (
          comments.map((item) => (
            <article className="comment-item" key={item.id}>
              <div className="comment-avatar" aria-hidden="true">
                {(item.author_name || "?").trim().charAt(0).toUpperCase()}
              </div>
              <div className="comment-content">
                <div className="comment-meta">
                  <strong>{item.author_name}</strong>
                  <time dateTime={item.created_at}>{formatCommentDate(item.created_at)}</time>
                </div>
                <p>{item.comment_text}</p>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
