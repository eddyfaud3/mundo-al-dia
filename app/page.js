import { getPool, initDb } from "../lib/db";
import SearchNews from "./components/SearchNews";
import NavigationMenu from "./components/NavigationMenu";

export const dynamic = "force-dynamic";

async function getNoticias() {
  try {
    await initDb();
    const { rows } = await getPool().query(
      "SELECT * FROM articles WHERE published=true ORDER BY created_at DESC"
    );
    return rows;
  } catch {
    return [];
  }
}

export default async function Home() {
  const noticias = await getNoticias();
  const destacada = noticias[0] || null;

  return (
    <main>
      <header className="header">
        <div className="container nav">
          <a href="/" className="logo logo-brand" aria-label="Mundo al Día, inicio">
            <img src="/logo-mundo-al-dia.svg" alt="Mundo al Día — Las noticias que importan, de todo el mundo" />
          </a>
          <NavigationMenu />
        </div>
      </header>

      <section className="hero">
        <div className="container">
          <p className="eyebrow">INFORMACIÓN GLOBAL</p>
          <h1>El mundo, al día.</h1>
          <p>Las noticias más importantes del mundo, reunidas en un solo lugar.</p>
          <a className="button" href="#ultimas">Ver últimas noticias</a>
        </div>
      </section>

      {destacada && (
        <section className="container featured-section" aria-labelledby="featured-title">
          <div className="featured-heading">
            <span className="featured-label">NOTICIA DESTACADA</span>
            {destacada.category && destacada.category.trim().toLowerCase() !== (destacada.title || "").trim().toLowerCase() && (
              <span className="featured-category">{destacada.category}</span>
            )}
          </div>
          <a className="featured-card" href={`/noticia/${destacada.slug}`}>
            {destacada.image_url ? (
              <img className="featured-image" src={destacada.image_url} alt={destacada.title} />
            ) : (
              <div className="featured-image featured-image-placeholder" aria-hidden="true">🌎</div>
            )}
            <div className="featured-content">
              <h2 id="featured-title">{destacada.title}</h2>
              {destacada.excerpt && <p>{destacada.excerpt}</p>}
              <span className="featured-read">Leer noticia completa →</span>
            </div>
          </a>
        </section>
      )}

      <section id="ultimas" className="container news-section">
        <div className="section-title">
          <h2>Últimas noticias</h2>
          <p>Información que importa.</p>
        </div>

        {noticias.length === 0 ? (
          <p>No hay noticias publicadas todavía.</p>
        ) : (
          <SearchNews noticias={noticias} featuredId={destacada?.id} />
        )}
      </section>

      <section className="cta">
        <div className="container">
          <h2>Ayúdanos a crecer</h2>
          <p>Comparte Mundo al Día y síguenos para recibir las noticias más importantes.</p>
        </div>
      </section>

      <footer id="contacto">
        <div className="container">
          <strong>🌎 Mundo al Día</strong>
          <p>Noticias globales, al día.</p>
          <p>Contacto: <a href="mailto:mundoaldia238@gmail.com">mundoaldia238@gmail.com</a></p>
        </div>
      </footer>
    </main>
  );
}
