import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../lib/auth";
import { getPool, initDb } from "../../../../lib/db";
import { publishArticleToFacebook } from "../../../../lib/facebook";

async function auth() {
  const token = cookies().get(cookieName)?.value;
  if (!validToken(token)) return null;
  await initDb();
  return getPool();
}

export async function GET() {
  try {
    const db = await auth();
    if (!db) return NextResponse.json({error:"No autorizado."},{status:401});
    const {rows} = await db.query("SELECT * FROM articles ORDER BY created_at DESC");
    return NextResponse.json(rows);
  } catch (e) {
    return NextResponse.json({error:e.message},{status:500});
  }
}

export async function POST(request) {
  try {
    const db = await auth();
    if (!db) return NextResponse.json({error:"No autorizado."},{status:401});
    const a = await request.json();
    const {rows} = await db.query(
      `INSERT INTO articles (title,slug,excerpt,content,image_url,video_url,category,published)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING *`,
      [a.title,a.slug,a.excerpt||"",a.content||"",a.image_url||"",a.video_url||"",a.category||"Mundo",!!a.published]
    );

    const article = rows[0];
    let facebook = null;
    if (article.published) {
      try {
        facebook = await publishArticleToFacebook(article);
        if (facebook.published) {
          await db.query("UPDATE articles SET facebook_post_id=$1,updated_at=NOW() WHERE id=$2", [
            facebook.postId,
            article.id,
          ]);
          article.facebook_post_id = facebook.postId;
        }
      } catch (facebookError) {
        facebook = { published:false, reason:facebookError.message };
      }
    }

    return NextResponse.json({ ...article, facebook }, {status:201});
  } catch(e) {
    return NextResponse.json({error:e.message},{status:400});
  }
}
