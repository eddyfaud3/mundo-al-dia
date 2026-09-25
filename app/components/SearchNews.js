"use client";

import { useMemo, useState } from "react";

export default function SearchNews({ noticias }) {
  const [query, setQuery] = useState("");

  const resultados = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return noticias;
    return noticias.filter((n) =>
      [n.title, n.excerpt, n.content, n.category]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(q))
    );
  }, [query, noticias]);

  return (
    <div className="search-wrap">
      <label htmlFor="news-search">Buscar noticias</label>
      <div className="search-box">
        <input
          id="news-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Busca por título, tema o categoría..."
          aria-label="Buscar noticias"
        />
        <span>🔎</span>
      </div>

      {query.trim() && (
        <p className="search-count">
          {resultados.length} {resultados.length === 1 ? "resultado" : "resultados"}
        </p>
      )}

      {resultados.length === 0 ? (
        <p className="no-results">No encontramos noticias con esa búsqueda.</p>
      ) : (
        <div className="news-grid">
          {resultados.map((noticia) => (
            <article className="card" key={noticia.id}>
              {noticia.image_url && <img src={noticia.image_url} alt={noticia.title} />}
              <div className="card-content">
                <span>{noticia.category}</span>
                <h3>{noticia.title}</h3>
                <p>{noticia.excerpt}</p>
                <a href={`/noticia/${noticia.slug}`}>Leer noticia →</a>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
