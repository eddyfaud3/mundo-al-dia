import { getPool, initDb } from "../lib/db";
import SearchNews from "./components/SearchNews";

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

  return (
    <main>
      <header className="header">
        <div className="container nav">
          <div className="logo">🌎 Mundo al Día</div>
          <nav>
            <a href="/">Inicio</a>
            <a href="#ultimas">Últimas noticias</a>
            <a href="#contacto">Contacto</a>
          </nav>
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

      <section id="ultimas" className="container news-section">
        <div className="section-title">
          <h2>Últimas noticias</h2>
          <p>Información que importa.</p>
        </div>

        {noticias.length === 0 ? (
          <p>No hay noticias publicadas todavía.</p>
        ) : (
          <SearchNews noticias={noticias} />
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
        </div>
      </footer>
    </main>
  );
}
