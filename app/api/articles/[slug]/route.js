import { NextResponse } from "next/server";
import { getPool, initDb } from "../../../../lib/db";

export async function GET(request,{params}) {
  try {
    await initDb();
    const {rows}=await getPool().query("SELECT * FROM articles WHERE published=true AND slug=$1 LIMIT 1",[params.slug]);
    if(!rows[0]) return NextResponse.json({error:"Noticia no encontrada."},{status:404});
    return NextResponse.json(rows[0]);
  } catch(e) {
    return NextResponse.json({error:e.message},{status:500});
  }
}
