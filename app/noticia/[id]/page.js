import { getPool, initDb } from "../../../lib/db";

export const dynamic = "force-dynamic";

async function getNoticia(slug) {
  try {
    await initDb();
    const { rows } = await getPool().query(
      "SELECT * FROM articles WHERE slug=$1 AND published=true LIMIT 1",
      [slug]
    );
    return rows[0] || null;
  } catch {
    return null;
  }
}

export default async function NoticiaPage({ params }) {
  const noticia = await getNoticia(params.id);

  if (!noticia) {
    return (
      <main className="container news-section">
        <h1>Noticia no encontrada</h1>
        <a href="/">← Volver al inicio</a>
      </main>
    );
  }

  return (
    <main>
      <header className="header">
        <div className="container nav">
          <div className="logo">🌎 Mundo al Día</div>
          <a href="/">← Inicio</a>
        </div>
      </header>

      <article className="container news-section">
        <span>{noticia.category}</span>
        <h1>{noticia.title}</h1>
        {noticia.image_url && <img src={noticia.image_url} alt={noticia.title} style={{ width: "100%", maxWidth: 1200, borderRadius: 12, margin: "20px 0" }} />}
        {noticia.video_url && (
          <p><a href={noticia.video_url} target="_blank" rel="noreferrer">▶ Ver video</a></p>
        )}
        {noticia.excerpt && <p><strong>{noticia.excerpt}</strong></p>}
        <div style={{ whiteSpace: "pre-wrap" }}>{noticia.content}</div>

        <div className="cta">
          <h2>Sigue informado</h2>
          <p>Comparte Mundo al Día y síguenos para recibir las noticias más importantes.</p>
        </div>
      </article>
    </main>
  );
}
