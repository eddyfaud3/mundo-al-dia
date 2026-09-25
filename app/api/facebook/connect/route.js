import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";
import { cookieName, validToken } from "../../../../lib/auth";
import { facebookConfigured, facebookLoginUrl } from "../../../../lib/facebook";

export async function GET() {
  if (!validToken(cookies().get(cookieName)?.value)) {
    return NextResponse.redirect(new URL("/admin/login", process.env.NEXT_PUBLIC_SITE_URL || "https://mundo-al-dia-github-production.up.railway.app"));
  }
  if (!facebookConfigured()) {
    return NextResponse.json(
      { error:"Facebook todavía no está configurado. Faltan las variables META_APP_ID y META_APP_SECRET en Railway." },
      { status:503 }
    );
  }

  const state = crypto.randomBytes(24).toString("hex");
  const response = NextResponse.redirect(facebookLoginUrl(state));
  response.cookies.set("mundo_fb_oauth_state", state, {
    httpOnly:true,
    secure:true,
    sameSite:"lax",
    maxAge:600,
    path:"/",
  });
  return response;
}
