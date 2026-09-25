import { NextResponse } from "next/server";
import { getPool, initDb } from "../../../lib/db";

export async function GET() {
  try {
    await initDb();
    const {rows}=await getPool().query("SELECT * FROM articles WHERE published=true ORDER BY created_at DESC");
    return NextResponse.json(rows);
  } catch(e) {
    return NextResponse.json({error:e.message},{status:500});
  }
}
