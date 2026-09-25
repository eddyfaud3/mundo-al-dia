import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../../lib/auth";
import { getPool, initDb } from "../../../../../lib/db";

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
    const {rows}=await db.query(
      `UPDATE articles SET title=$1,slug=$2,excerpt=$3,content=$4,image_url=$5,video_url=$6,category=$7,published=$8,updated_at=NOW()
       WHERE id=$9 RETURNING *`,
      [a.title,a.slug,a.excerpt||"",a.content||"",a.image_url||"",a.video_url||"",a.category||"Mundo",!!a.published,params.id]
    );
    if(!rows[0]) return NextResponse.json({error:"Noticia no encontrada."},{status:404});
    return NextResponse.json(rows[0]);
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
