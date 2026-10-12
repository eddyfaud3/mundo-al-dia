import { NextResponse } from "next/server";
import { getPool, initDb } from "../../../../../lib/db";

export const dynamic = "force-dynamic";

export async function GET(request, { params }) {
  try {
    await initDb();
    const db = getPool();
    const article = await db.query(
      "SELECT id FROM articles WHERE slug=$1 AND published=true LIMIT 1",
      [params.slug]
    );
    if (!article.rows[0]) {
      return NextResponse.json({ error: "Noticia no encontrada." }, { status: 404 });
    }

    const result = await db.query(
      `SELECT id, author_name, comment_text, created_at
       FROM article_comments
       WHERE article_id=$1
       ORDER BY created_at DESC
       LIMIT 50`,
      [article.rows[0].id]
    );
    return NextResponse.json({ comments: result.rows });
  } catch {
    return NextResponse.json({ error: "No se pudieron cargar los comentarios." }, { status: 500 });
  }
}

export async function POST(request, { params }) {
  try {
    const body = await request.json();
    const name = typeof body.name === "string" ? body.name.trim().replace(/\\s+/g, " ") : "";
    const comment = typeof body.comment === "string" ? body.comment.trim() : "";

    if (name.length < 2 || name.length > 50) {
      return NextResponse.json({ error: "Escribe un nombre de entre 2 y 50 caracteres." }, { status: 400 });
    }
    if (comment.length < 3 || comment.length > 1000) {
      return NextResponse.json({ error: "El comentario debe tener entre 3 y 1000 caracteres." }, { status: 400 });
    }

    await initDb();
    const db = getPool();
    const article = await db.query(
      "SELECT id FROM articles WHERE slug=$1 AND published=true LIMIT 1",
      [params.slug]
    );
    if (!article.rows[0]) {
      return NextResponse.json({ error: "Noticia no encontrada." }, { status: 404 });
    }

    const inserted = await db.query(
      `INSERT INTO article_comments (article_id, author_name, comment_text)
       VALUES ($1, $2, $3)
       RETURNING id, author_name, comment_text, created_at`,
      [article.rows[0].id, name, comment]
    );
    return NextResponse.json({ comment: inserted.rows[0] }, { status: 201 });
  } catch {
    return NextResponse.json({ error: "No se pudo publicar el comentario. Inténtalo de nuevo." }, { status: 500 });
  }
}
