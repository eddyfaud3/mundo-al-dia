import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../lib/auth";
import { disconnectFacebook } from "../../../../lib/facebook";

export async function POST() {
  if (!validToken(cookies().get(cookieName)?.value)) {
    return NextResponse.json({error:"No autorizado."},{status:401});
  }
  await disconnectFacebook();
  return NextResponse.json({ok:true});
}
