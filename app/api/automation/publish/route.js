import { NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { getPool, initDb } from "../../../../lib/db";
import { publishArticleToFacebook } from "../../../../lib/facebook";

export const runtime = "nodejs";

function authorized(request) {
  const expected = process.env.AUTOMATION_PUBLISH_SECRET || "";
  const supplied = request.headers.get("authorization") || "";
  const prefix = "Bearer ";
  if (!expected || !supplied.startsWith(prefix)) return false;
  const candidate = supplied.slice(prefix.length);
  const a = Buffer.from(candidate);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

function validText(value, max) {
  return typeof value === "string" && value.trim().length > 0 && value.length <= max;
}

export async function POST(request) {
  if (!authorized(request)) {
    return NextResponse.json({ error: "No autorizado." }, { status: 401 });
  }

  try {
    const body = await request.json();
    const title = typeof body.title === "string" ? body.title.trim() : "";
    const slug = typeof body.slug === "string" ? body.slug.trim() : "";
    const excerpt = typeof body.excerpt === "string" ? body.excerpt.trim() : "";
    const content = typeof body.content === "string" ? body.content.trim() : "";
    const category = typeof body.category === "string" ? body.category.trim() : "Mundo";
    const image_url = typeof body.image_url === "string" ? body.image_url.trim() : "";
    const video_url = typeof body.video_url === "string" ? body.video_url.trim() : "";

    if (!validText(title, 220) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 180 || !validText(content, 30000)) {
      return NextResponse.json({ error: "Datos inválidos: revisa title, slug y content." }, { status: 400 });
    }
    if (excerpt.length > 1200 || category.length > 80 || image_url.length > 2000 || video_url.length > 2000) {
      return NextResponse.json({ error: "Uno de los campos supera el límite permitido." }, { status: 400 });
    }
    for (const url of [image_url, video_url].filter(Boolean)) {
      try {
        if (new URL(url).protocol !== "https:") throw new Error();
      } catch {
        return NextResponse.json({ error: "Las URL de foto o video deben usar HTTPS." }, { status: 400 });
      }
    }

    await initDb();
    const db = getPool();
    const existing = await db.query("SELECT id FROM articles WHERE slug=$1 LIMIT 1", [slug]);
    if (existing.rows.length) {
      return NextResponse.json({ error: "Ya existe una noticia con ese slug; no se publicó otra vez." }, { status: 409 });
    }

    const inserted = await db.query(
      `INSERT INTO articles (title,slug,excerpt,content,image_url,video_url,category,published)
       VALUES ($1,$2,$3,$4,$5,$6,$7,true) RETURNING *`,
      [title, slug, excerpt, content, image_url, video_url, category || "Mundo"]
    );
    const article = inserted.rows[0];
    let facebook = { published: false, reason: "No se pudo confirmar la publicación en Facebook." };
    try {
      facebook = await publishArticleToFacebook(article);
      if (facebook.published && facebook.postId) {
        await db.query("UPDATE articles SET facebook_post_id=$1,updated_at=NOW() WHERE id=$2", [facebook.postId, article.id]);
      }
    } catch (error) {
      facebook = { published: false, reason: error?.message || "Error de Facebook." };
    }

    return NextResponse.json({
      published: true,
      id: article.id,
      title: article.title,
      url: `${process.env.NEXT_PUBLIC_SITE_URL || "https://mundo-al-dia-github-production.up.railway.app"}/noticia/${encodeURIComponent(article.slug)}`,
      facebook,
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error?.message || "No se pudo publicar la noticia." }, { status: 500 });
  }
}
