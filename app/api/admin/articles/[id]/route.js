import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../../lib/auth";
import { getPool, initDb } from "../../../../../lib/db";
import { publishArticleToFacebook } from "../../../../../lib/facebook";

async function auth() {
  if (!validToken(cookies().get(cookieName)?.value)) return null;
  await initDb();
  return getPool();
}

export async function PUT(request,{params}) {
  try {
    const db=await auth();
    if(!db) return NextResponse.json({error:"No autorizado."},{status:401});
    const a=await request.json();

    const existing = await db.query(
      "SELECT published,facebook_post_id FROM articles WHERE id=$1 LIMIT 1",
      [params.id]
    );
    if (!existing.rows[0]) {
      return NextResponse.json({error:"Noticia no encontrada."},{status:404});
    }

    const wasPublished = Boolean(existing.rows[0].published);
    const alreadyPosted = Boolean(existing.rows[0].facebook_post_id);

    const {rows}=await db.query(
      `UPDATE articles SET title=$1,slug=$2,excerpt=$3,content=$4,image_url=$5,video_url=$6,category=$7,published=$8,updated_at=NOW()
       WHERE id=$9 RETURNING *`,
      [a.title,a.slug,a.excerpt||"",a.content||"",a.image_url||"",a.video_url||"",a.category||"Mundo",!!a.published,params.id]
    );
    if(!rows[0]) return NextResponse.json({error:"Noticia no encontrada."},{status:404});

    const article = rows[0];
    let facebook = null;

    if (article.published && (!wasPublished || !alreadyPosted)) {
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

    return NextResponse.json({ ...article, facebook });
  }catch(e){return NextResponse.json({error:e.message},{status:400});}
}

export async function DELETE(request,{params}) {
  try {
    const db=await auth();
    if(!db) return NextResponse.json({error:"No autorizado."},{status:401});
    await db.query("DELETE FROM articles WHERE id=$1",[params.id]);
    return NextResponse.json({ok:true});
  }catch(e){return NextResponse.json({error:e.message},{status:500});}
}
