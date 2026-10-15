import { Pool } from "pg";

let pool;

export function getPool() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL no está configurada en Railway.");
  }
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false },
    });
  }
  return pool;
}

export async function initDb() {
  const db = getPool();
  await db.query(`
    CREATE TABLE IF NOT EXISTS articles (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      slug TEXT UNIQUE NOT NULL,
      excerpt TEXT DEFAULT '',
      content TEXT DEFAULT '',
      image_url TEXT DEFAULT '',
      video_url TEXT DEFAULT '',
      category TEXT DEFAULT 'Mundo',
      published BOOLEAN NOT NULL DEFAULT false,
      facebook_post_id TEXT DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);
  await db.query("ALTER TABLE articles ADD COLUMN IF NOT EXISTS facebook_post_id TEXT DEFAULT ''");
  await db.query("ALTER TABLE articles ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0");
  await db.query("ALTER TABLE articles ADD COLUMN IF NOT EXISTS like_count INTEGER NOT NULL DEFAULT 0");
  await db.query(`
    CREATE TABLE IF NOT EXISTS article_likes (
      article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
      client_key TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (article_id, client_key)
    )
  `);

  await db.query(`
    CREATE TABLE IF NOT EXISTS article_comments (
      id SERIAL PRIMARY KEY,
      article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
      author_name VARCHAR(50) NOT NULL,
      comment_text VARCHAR(1000) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);


  const count = await db.query("SELECT COUNT(*)::int AS count FROM articles");
  if (count.rows[0].count === 0) {
    await db.query(`
      INSERT INTO articles (title, slug, excerpt, content, image_url, category, published)
      VALUES
      ('Las noticias más importantes del mundo', 'las-noticias-mas-importantes-del-mundo', 'Mantente informado con las noticias y acontecimientos más relevantes de todo el mundo.', 'Mundo al Día te mantiene informado sobre los acontecimientos más importantes de todo el mundo.', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80', 'Mundo', true),
      ('Últimas noticias y acontecimientos internacionales', 'ultimas-noticias-y-acontecimientos-internacionales', 'Información actualizada sobre los acontecimientos que están marcando la actualidad mundial.', 'Conoce los acontecimientos internacionales que están marcando la actualidad.', 'https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1200&q=80', 'Internacional', true),
      ('Información que importa', 'informacion-que-importa', 'Noticias verificadas, imágenes y videos para mantenerte al día.', 'Noticias, imágenes y videos para mantenerte informado.', 'https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=1200&q=80', 'Actualidad', true)
    `);
  }

  await db.query(`
    INSERT INTO articles (title, slug, excerpt, content, image_url, video_url, category, published)
    VALUES (
      '🚨 ALERTA EN REINO UNIDO: cinco detenidos cerca de una base militar por una posible amenaza terrorista',
      'alerta-reino-unido-cinco-detenidos-base-militar-posible-amenaza-terrorista',
      'Cinco hombres fueron detenidos cerca de la base aérea RAF Fairford mientras la policía antiterrorista británica investiga una posible amenaza relacionada con explosivos.',
      'La policía antiterrorista del Reino Unido investiga un incidente ocurrido cerca de la base aérea RAF Fairford, en Gloucestershire. Cinco hombres, de entre 23 y 25 años, fueron detenidos bajo sospecha de delitos relacionados con explosivos y de preparar un posible acto terrorista. Las autoridades reportaron vehículos sospechosos, desplegaron agentes armados y evacuaron temporalmente a residentes de la zona. La investigación continúa y, hasta el momento, no se ha confirmado que haya ocurrido un atentado ni que los detenidos hayan sido acusados formalmente. La información se presenta como una investigación por una posible amenaza, no como un ataque confirmado.',
      '',
      '',
      'Internacional',
      true
    )
    ON CONFLICT (slug) DO UPDATE SET
      title=EXCLUDED.title,
      excerpt=EXCLUDED.excerpt,
      content=EXCLUDED.content,
      category=EXCLUDED.category,
      published=true,
      updated_at=NOW()
  `);

  await db.query(`
    INSERT INTO articles (title, slug, excerpt, content, image_url, video_url, category, published)
    VALUES (
      '🚨 ÚLTIMA HORA: Inundaciones en Estambul dejan 3 muertos y 4 desaparecidos',
      'inundaciones-estambul-turquia-tres-muertos-cuatro-desaparecidos-15-octubre-2026',
      'Las fuertes lluvias inundaron viviendas, comercios y carreteras de Estambul. Las autoridades reportan tres fallecidos, cuatro desaparecidos y más de 2.700 personas rescatadas.',
      'ESTAMBUL, Turquía — 15 de octubre de 2026.\n\nUna intensa tormenta provocó graves inundaciones en Estambul durante la noche del miércoles, anegando viviendas, comercios, carreteras y pasos subterráneos. Varios vehículos quedaron atrapados y se registraron importantes problemas de circulación.\n\nLas autoridades informaron de al menos tres personas fallecidas y cuatro desaparecidas. El ministro del Interior indicó que más de 2.700 personas que quedaron atrapadas por las inundaciones fueron evacuadas de manera segura.\n\nLa municipalidad de Estambul señaló que algunas zonas registraron niveles de lluvia que no se observaban desde 1985. Las autoridades recomendaron evitar desplazamientos innecesarios, extendieron el cierre de las escuelas hasta el viernes y restringieron la circulación de motocicletas. Se pronostican más lluvias para los próximos días.\n\nMundo al Día seguirá atento a las actualizaciones.\n\nFuente: Associated Press (AP), 15 de octubre de 2026: https://apnews.com/article/51f3d03c2662b8b5d50098ae6a069a80',
      '',
      '',
      'Internacional',
      true
    )
    ON CONFLICT (slug) DO NOTHING
  `);

  await db.query(`
    INSERT INTO articles (title, slug, excerpt, content, image_url, video_url, category, published)
    VALUES (
      '🚨 ¡TERRIBLE INUNDACIÓN EN TURQUÍA! La corriente provoca el colapso de una vivienda',
      'inundacion-sakarya-turquia-casa-colapsa-video-15-octubre-2026',
      'Las fuertes lluvias desbordaron un arroyo en Sakarya y provocaron el derrumbe de una vivienda de dos pisos que ya había sido evacuada. No se reportaron víctimas por este colapso.',
      'SAKARYA, Turquía — 15 de octubre de 2026.\n\nLas intensas lluvias provocaron inundaciones repentinas en el distrito de Sapanca, en la provincia de Sakarya, al noroeste de Turquía. En el barrio de Fevziye, un arroyo se desbordó y la corriente provocó el colapso de una vivienda de dos pisos situada junto al cauce.\n\nSegún Anadolu Agency, la casa había sido evacuada previamente y no se reportaron fallecidos ni heridos por el derrumbe. Las inundaciones también dañaron un puente y postes eléctricos, y dificultaron el acceso al barrio mientras los equipos de emergencia atendían la zona.\n\nLas lluvias también causaron graves inundaciones en Estambul, donde Associated Press informó de al menos tres fallecidos y cuatro personas desaparecidas. Esos reportes corresponden a incidentes en Estambul, no al colapso de la vivienda en Sakarya.\n\nLas autoridades mantienen las labores de emergencia y han pedido a la población que permanezca alerta ante el riesgo de nuevas precipitaciones.\n\nFuentes: Anadolu Agency, 15 de octubre de 2026; Associated Press: https://apnews.com/article/51f3d03c2662b8b5d50098ae6a069a80',
      '',
      'https://aa.com.tr/en/vg/video-gallery/heavy-rains-cause-house-collapse-in-turkiye-s-sakarya-province/157118',
      'Internacional',
      true
    )
    ON CONFLICT (slug) DO NOTHING
  `);
}
