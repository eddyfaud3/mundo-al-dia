const noticias = {
  "1": {
    categoria: "Mundo",
    titulo: "Las noticias más importantes del mundo",
    texto: "Mundo al Día te mantiene informado sobre los acontecimientos más importantes de todo el mundo."
  },
  "2": {
    categoria: "Internacional",
    titulo: "Últimas noticias y acontecimientos internacionales",
    texto: "Conoce los acontecimientos internacionales que están marcando la actualidad."
  },
  "3": {
    categoria: "Actualidad",
    titulo: "Información que importa",
    texto: "Noticias, imágenes y videos para mantenerte informado."
  }
};

export default function NoticiaPage({ params }) {
  const noticia = noticias[params.id];

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
        <span>{noticia.categoria}</span>
        <h1>{noticia.titulo}</h1>
        <p>{noticia.texto}</p>

        <div className="cta">
          <h2>Sigue informado</h2>
          <p>
            Comparte Mundo al Día y síguenos para recibir las noticias más importantes.
          </p>
        </div>
      </article>
    </main>
  );
}
