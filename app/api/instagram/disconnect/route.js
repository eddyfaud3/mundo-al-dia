import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../lib/auth";
import { disconnectInstagram } from "../../../../lib/facebook";

export async function POST() {
  if (!validToken(cookies().get(cookieName)?.value)) {
    return NextResponse.json({ error: "No autorizado." }, { status: 401 });
  }
  await disconnectInstagram();
  return NextResponse.json({ ok: true });
}
