"use client";

import { useMemo, useState } from "react";

export default function SearchNews({ noticias, featuredId }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("Todas");

  const categories = useMemo(() => ["Todas", ...new Set(noticias.map((n) => n.category).filter(Boolean))], [noticias]);

  const resultados = useMemo(() => {
    const q = query.trim().toLowerCase();
    return noticias.filter((n) => {
      const matchesCategory = category === "Todas" || n.category === category;
      const matchesQuery = [n.title, n.excerpt, n.content, n.category]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(q));
      const shouldHideFeatured = Boolean(featuredId) && n.id === featuredId && !q && category === "Todas";
      return matchesCategory && matchesQuery && !shouldHideFeatured;
    });
  }, [query, category, noticias, featuredId]);

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
        <span aria-hidden="true">🔎</span>
      </div>

      <div className="category-filter" role="group" aria-label="Filtrar por categoría">
        {categories.map((item) => (
          <button
            key={item}
            type="button"
            className={category === item ? "active" : ""}
            onClick={() => setCategory(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {(query.trim() || category !== "Todas") && (
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
