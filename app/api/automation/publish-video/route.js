import { NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { getPool, initDb } from "../../../../lib/db";
import { publishVideoToFacebook, publishVideoToInstagram } from "../../../../lib/facebook";

export const runtime = "nodejs";

function authorized(request) {
  const expected = process.env.AUTOMATION_PUBLISH_SECRET || process.env.MUNDO_AL_DIA_AUTOMATION_SECRET || "";
  const supplied = request.headers.get("authorization") || "";
  if (!expected || !supplied.startsWith("Bearer ")) return false;

  const candidate = Buffer.from(supplied.slice(7));
  const secret = Buffer.from(expected);
  return candidate.length === secret.length && timingSafeEqual(candidate, secret);
}

function makeSlug(value) {
  const base = String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 135)
    .replace(/-+$/g, "");
  return base || "video-noticia";
}

export async function POST(request) {
  if (!authorized(request)) {
    return NextResponse.json({ error: "No autorizado." }, { status: 401 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido." }, { status: 400 });
  }

  const title = typeof body.title === "string" ? body.title.trim() : "";
  const caption = typeof body.caption === "string" ? body.caption.trim() : title;
  const videoUrl = typeof body.video_url === "string" ? body.video_url.trim() : "";
  const runId = String(body.run_id || Date.now().toString(36)).trim();

  if (!title || title.length > 220 || !caption || caption.length > 1200) {
    return NextResponse.json({ error: "Revisa el título y el texto del vídeo." }, { status: 400 });
  }
  try {
    if (new URL(videoUrl).protocol !== "https:") throw new Error();
  } catch {
    return NextResponse.json({ error: "La URL del vídeo debe ser HTTPS." }, { status: 400 });
  }
  if (!/^[a-zA-Z0-9_-]{1,80}$/.test(runId)) {
    return NextResponse.json({ error: "Identificador de ejecución inválido." }, { status: 400 });
  }

  // Keep the public path closed unless the Railway switch is explicitly enabled.
  if (process.env.VIDEO_AUTO_PUBLISH_ENABLED !== "true") {
    return NextResponse.json({
      ok: true,
      dry_run: true,
      message: "Solicitud validada; no se guardó ninguna noticia ni se publicó en redes.",
      title,
      video_url: videoUrl
    });
  }

  try {
    await initDb();
    const db = getPool();
    const slug = `${makeSlug(title)}-${runId}`.slice(0, 180);
    const existing = await db.query("SELECT id FROM articles WHERE slug=$1 LIMIT 1", [slug]);
    if (existing.rows.length) {
      return NextResponse.json({ error: "Esta ejecución ya fue procesada; se evita duplicar la publicación." }, { status: 409 });
    }

    const content = [caption, "", "Vídeo original de Mundo al Día."].join("\n");
    const inserted = await db.query(
      `INSERT INTO articles (title,slug,excerpt,content,image_url,video_url,category,published)
       VALUES ($1,$2,$3,$4,$5,$6,$7,true) RETURNING *`,
      [title, slug, caption, content, "", videoUrl, "Vídeo"]
    );
    const article = inserted.rows[0];

    let facebook = { published: false, reason: "No se pudo confirmar la publicación en Facebook." };
    try {
      facebook = await publishVideoToFacebook(article);
      if (facebook.published && facebook.postId) {
        await db.query("UPDATE articles SET facebook_post_id=$1,updated_at=NOW() WHERE id=$2", [facebook.postId, article.id]);
      }
    } catch (error) {
      facebook = { published: false, reason: error?.message || "Error de Facebook." };
    }

    let instagram = { published: false, reason: "Instagram no está conectado." };
    try {
      instagram = await publishVideoToInstagram(article);
    } catch (error) {
      instagram = { published: false, reason: error?.message || "Error de Instagram." };
    }

    return NextResponse.json({
      ok: true,
      site_published: true,
      social_publication: { facebook: Boolean(facebook.published), instagram: Boolean(instagram.published) },
      id: article.id,
      title: article.title,
      url: `${process.env.NEXT_PUBLIC_SITE_URL || "https://mundo-al-dia-github-production.up.railway.app"}/noticia/${encodeURIComponent(article.slug)}`,
      facebook,
      instagram
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error?.message || "No se pudo procesar el vídeo." }, { status: 500 });
  }
}
