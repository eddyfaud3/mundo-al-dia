import { getPool, initDb } from "../../../lib/db";

export const dynamic = "force-dynamic";

const baseUrl = "https://mundo-al-dia-github-production.up.railway.app";

function escapeXml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  await initDb();
  const { rows } = await getPool().query(
    "SELECT title, slug, excerpt, created_at FROM articles WHERE published=true ORDER BY created_at DESC LIMIT 50"
  );

  const items = rows.map((article) => `
    <item>
      <title>${escapeXml(article.title)}</title>
      <link>${baseUrl}/noticia/${article.slug}</link>
      <guid isPermaLink="true">${baseUrl}/noticia/${article.slug}</guid>
      <description>${escapeXml(article.excerpt || "")}</description>
      <pubDate>${new Date(article.created_at).toUTCString()}</pubDate>
    </item>`).join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Mundo al Día</title>
    <link>${baseUrl}</link>
    <description>Las noticias más importantes del mundo, al día.</description>
    <language>es</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600"
    }
  });
}
