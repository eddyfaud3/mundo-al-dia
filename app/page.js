const noticias = [
  {
    id: "1",
    titulo: "Las noticias más importantes del mundo",
    categoria: "Mundo",
    resumen: "Mantente informado con las noticias y acontecimientos más relevantes de todo el mundo.",
    imagen: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"
  },
  {
    id: "2",
    titulo: "Últimas noticias y acontecimientos internacionales",
    categoria: "Internacional",
    resumen: "Información actualizada sobre los acontecimientos que están marcando la actualidad mundial.",
    imagen: "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1200&q=80"
  },
  {
    id: "3",
    titulo: "Información que importa",
    categoria: "Actualidad",
    resumen: "Noticias verificadas, imágenes y videos para mantenerte al día.",
    imagen: "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=1200&q=80"
  }
];

export default function Home() {
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
          <p>
            Las noticias más importantes del mundo, reunidas en un solo lugar.
          </p>
          <a className="button" href="#ultimas">Ver últimas noticias</a>
        </div>
      </section>

      <section id="ultimas" className="container news-section">
        <div className="section-title">
          <h2>Últimas noticias</h2>
          <p>Información que importa.</p>
        </div>

        <div className="news-grid">
          {noticias.map((noticia) => (
            <article className="card" key={noticia.id}>
              <img src={noticia.imagen} alt={noticia.titulo} />
              <div className="card-content">
                <span>{noticia.categoria}</span>
                <h3>{noticia.titulo}</h3>
                <p>{noticia.resumen}</p>
                <a href={`/noticia/${noticia.id}`}>Leer noticia →</a>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="cta">
        <div className="container">
          <h2>Ayúdanos a crecer</h2>
          <p>
            Comparte Mundo al Día y síguenos para recibir las noticias más importantes.
          </p>
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
