import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";
import { cookieName, validToken } from "../../../../lib/auth";
import { facebookConfigured, facebookLoginUrl } from "../../../../lib/facebook";

function createOAuthState() {
  const nonce = crypto.randomBytes(24).toString("hex");
  const secret = process.env.META_APP_SECRET || process.env.ADMIN_PASSWORD || "";
  const signature = crypto.createHmac("sha256", secret).update(nonce).digest("hex");
  return `${nonce}.${signature}`;
}

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

  const state = createOAuthState();
  return NextResponse.redirect(facebookLoginUrl(state));
}
