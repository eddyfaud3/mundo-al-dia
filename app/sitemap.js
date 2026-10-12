import { getPool } from "../lib/db";

const baseUrl = "https://mundo-al-dia-github-production.up.railway.app";

// The sitemap must read published articles at request time, not during build.
export const dynamic = "force-dynamic";

export default async function sitemap() {
  const { rows } = await getPool().query(
    "SELECT slug, updated_at FROM articles WHERE published = true ORDER BY updated_at DESC"
  );

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    ...rows.map((article) => ({
      url: `${baseUrl}/noticia/${article.slug}`,
      lastModified: article.updated_at ? new Date(article.updated_at) : new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    })),
  ];
}
