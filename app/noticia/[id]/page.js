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

function getVideoEmbed(url) {
  if (!url) return null;

  try {
    const parsed = new URL(url);

    if (parsed.hostname.includes("youtube.com")) {
      const id = parsed.searchParams.get("v");
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }

    if (parsed.hostname === "youtu.be") {
      return `https://www.youtube.com/embed${parsed.pathname}`;
    }

    if (parsed.hostname.includes("vimeo.com")) {
      const id = parsed.pathname.split("/").filter(Boolean).pop();
      return id ? `https://player.vimeo.com/video/${id}` : null;
    }
  } catch {
    return null;
  }

  return null;
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function NoticiaPage({ params }) {
  const noticia = await getNoticia(params.id);

  if (!noticia) {
    return (
      <main className="container news-section not-found">
        <h1>Noticia no encontrada</h1>
        <p>La noticia que buscas no está disponible o ya no está publicada.</p>
        <a className="article-back" href="/">← Volver al inicio</a>
      </main>
    );
  }

  const embedUrl = getVideoEmbed(noticia.video_url);
  const isDirectVideo =
    noticia.video_url && !embedUrl
      ? /\.(mp4|webm|ogg)(\?.*)?$/i.test(noticia.video_url)
      : false;

  return (
    <main>
      <header className="header">
        <div className="container nav">
          <div className="logo">🌎 Mundo al Día</div>
          <a className="header-back" href="/">← Inicio</a>
        </div>
      </header>

      <article className="article-page">
        <div className="container">
          <div className="article-shell">
            <div className="article-top">
              <a className="article-back" href="/">← Volver a todas las noticias</a>
              <div className="article-category">{noticia.category || "Mundo"}</div>
              <h1>{noticia.title}</h1>

              {noticia.excerpt && (
                <p className="article-lead">{noticia.excerpt}</p>
              )}

              <div className="article-meta">
                <span>📰 Mundo al Día</span>
                {noticia.created_at && <span>• {formatDate(noticia.created_at)}</span>}
              </div>
            </div>

            {noticia.image_url && (
              <figure className="article-hero">
                <img src={noticia.image_url} alt={noticia.title} />
              </figure>
            )}

            {noticia.video_url && (
              <section className="article-media">
                <div className="media-heading">
                  <span>🎥</span>
                  <h2>Video de la noticia</h2>
                </div>

                {embedUrl ? (
                  <div className="video-frame">
                    <iframe
                      src={embedUrl}
                      title={`Video: ${noticia.title}`}
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                    />
                  </div>
                ) : isDirectVideo ? (
                  <video className="article-video" controls playsInline preload="metadata">
                    <source src={noticia.video_url} />
                    Tu navegador no puede reproducir este video.
                  </video>
                ) : (
                  <a
                    className="video-link"
                    href={noticia.video_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    ▶ Abrir video
                  </a>
                )}
              </section>
            )}

            <div className="article-body">
              {noticia.content
                ?.split(/\n\s*\n/)
                .filter(Boolean)
                .map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
            </div>

            <div className="article-share">
              <strong>¿Te pareció importante?</strong>
              <span>Comparte esta noticia y ayuda a crecer a Mundo al Día.</span>
              <a
                href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(
                  `/noticia/${noticia.slug}`
                )}`}
                target="_blank"
                rel="noreferrer"
              >
                Compartir en Facebook →
              </a>
            </div>
          </div>
        </div>
      </article>

      <section className="cta">
        <h2>Sigue informado</h2>
        <p>Comparte Mundo al Día y síguenos para recibir las noticias más importantes del mundo.</p>
      </section>
    </main>
  );
}
