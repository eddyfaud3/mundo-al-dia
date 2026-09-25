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
}
