import { NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { publishVideoToFacebook, publishVideoToInstagram } from "../../../../lib/facebook";

export const runtime = "nodejs";
export const maxDuration = 180;

function authorized(request) {
  const expected = process.env.AUTOMATION_PUBLISH_SECRET || "";
  const supplied = request.headers.get("authorization") || "";
  if (!expected || !supplied.startsWith("Bearer ")) return false;
  const a = Buffer.from(supplied.slice(7));
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(request) {
  if (!authorized(request)) return NextResponse.json({ error: "No autorizado." }, { status: 401 });

  // Two independent switches are required: the workflow's manual checkbox and
  // this Railway environment flag. Both remain off by default during testing.
  if (String(process.env.VIDEO_AUTO_PUBLISH_ENABLED || "").toLowerCase() !== "true") {
    return NextResponse.json({ error: "Publicación de vídeo desactivada; no se publicó nada." }, { status: 423 });
  }

  try {
    const body = await request.json();
    const title = typeof body.title === "string" ? body.title.trim() : "";
    const caption = typeof body.caption === "string" ? body.caption.trim() : "";
    const videoUrl = typeof body.video_url === "string" ? body.video_url.trim() : "";
    if (!title || title.length > 220 || caption.length > 2200 || !/^https:\/\//i.test(videoUrl) || videoUrl.length > 2000) {
      return NextResponse.json({ error: "Se requiere título, texto y URL HTTPS pública válida del MP4." }, { status: 400 });
    }
    const parsed = new URL(videoUrl);
    if (parsed.protocol !== "https:" || !/\.mp4(?:$|\?)/i.test(parsed.pathname + parsed.search)) {
      return NextResponse.json({ error: "La URL pública debe apuntar a un MP4 HTTPS." }, { status: 400 });
    }

    // These are real public posts. The double opt-in above deliberately blocks
    // this route until the owner enables publishing after tests are complete.
    const results = await Promise.allSettled([
      publishVideoToFacebook({ videoUrl, title, caption }),
      publishVideoToInstagram({ videoUrl, title, caption }),
    ]);
    const facebook = results[0].status === "fulfilled" ? results[0].value : { published: false, reason: results[0].reason?.message || "Error de Facebook." };
    const instagram = results[1].status === "fulfilled" ? results[1].value : { published: false, reason: results[1].reason?.message || "Error de Instagram." };
    const ok = facebook.published && instagram.published;
    return NextResponse.json({ published: ok, facebook, instagram }, { status: ok ? 200 : 502 });
  } catch (error) {
    return NextResponse.json({ error: error?.message || "No se pudo publicar el vídeo." }, { status: 500 });
  }
}
