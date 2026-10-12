import { NextResponse } from "next/server";
import { getPool, initDb } from "../../../../../lib/db";

export const dynamic = "force-dynamic";

export async function POST(request, { params }) {
  try {
    const slug = params.slug;
    const body = await request.json();
    const action = body?.action;

    if (!slug || !["view", "like"].includes(action)) {
      return NextResponse.json({ error: "Solicitud no válida." }, { status: 400 });
    }

    await initDb();
    const db = getPool();
    const found = await db.query(
      "SELECT id FROM articles WHERE slug=$1 AND published=true LIMIT 1",
      [slug]
    );

    if (!found.rows[0]) {
      return NextResponse.json({ error: "Noticia no encontrada." }, { status: 404 });
    }

    const articleId = found.rows[0].id;

    if (action === "view") {
      await db.query("UPDATE articles SET view_count = view_count + 1 WHERE id=$1", [articleId]);
    } else {
      const clientKey = typeof body.clientKey === "string" ? body.clientKey.slice(0, 100) : "";
      if (!/^[a-zA-Z0-9_-]{12,100}$/.test(clientKey)) {
        return NextResponse.json({ error: "Identificador no válido." }, { status: 400 });
      }

      const inserted = await db.query(
        "INSERT INTO article_likes (article_id, client_key) VALUES ($1,$2) ON CONFLICT DO NOTHING RETURNING article_id",
        [articleId, clientKey]
      );
      if (inserted.rowCount > 0) {
        await db.query("UPDATE articles SET like_count = like_count + 1 WHERE id=$1", [articleId]);
      }
    }

    const stats = await db.query(
      "SELECT view_count, like_count FROM articles WHERE id=$1",
      [articleId]
    );
    return NextResponse.json(stats.rows[0]);
  } catch (error) {
    return NextResponse.json({ error: "No se pudieron actualizar las estadísticas." }, { status: 500 });
  }
}
