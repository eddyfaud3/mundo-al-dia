import { getPool, initDb } from "../lib/db";

const baseUrl = "https://mundo-al-dia-github-production.up.railway.app";

export default async function sitemap() {
  try {
    await initDb();
    const { rows } = await getPool().query(
      "SELECT slug, updated_at FROM articles WHERE published=true ORDER BY updated_at DESC"
    );

    return [
      {
        url: baseUrl,
        lastModified: new Date()
      },
      ...rows.map((article) => ({
        url: `${baseUrl}/noticia/${article.slug}`,
        lastModified: article.updated_at ? new Date(article.updated_at) : new Date()
      }))
    ];
  } catch {
    return [{ url: baseUrl, lastModified: new Date() }];
  }
}
