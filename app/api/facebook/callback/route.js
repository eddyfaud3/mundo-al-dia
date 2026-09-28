import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";
import { saveFacebookAuthorization } from "../../../../lib/facebook";
import { cookieName, validToken } from "../../../../lib/auth";

function validOAuthState(state) {
  const parts = String(state || "").split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return false;
  const secret = process.env.META_APP_SECRET || process.env.ADMIN_PASSWORD || "";
  if (!secret) return false;
  const expected = crypto.createHmac("sha256", secret).update(parts[0]).digest("hex");
  const actual = Buffer.from(parts[1], "utf8");
  const expectedBuffer = Buffer.from(expected, "utf8");
  return actual.length === expectedBuffer.length && crypto.timingSafeEqual(actual, expectedBuffer);
}

export async function GET(request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const site = process.env.NEXT_PUBLIC_SITE_URL || "https://mundo-al-dia-github-production.up.railway.app";
  const redirect = (message) => NextResponse.redirect(new URL("/admin?facebook=" + encodeURIComponent(message), site));

  if (url.searchParams.get("error")) {
    const detail = url.searchParams.get("error_description") || url.searchParams.get("error");
    return redirect("error:" + detail);
  }

  if (!validOAuthState(state)) {
    return redirect("error:La sesión de conexión de Facebook no es válida. Intenta conectar de nuevo.");
  }

  if (!code) {
    return redirect("error:Facebook no devolvió el código de autorización.");
  }

  try {
    const page = await saveFacebookAuthorization(code);
    const response = NextResponse.redirect(new URL("/admin?facebook=connected&name=" + encodeURIComponent(page.name), site));
    response.cookies.delete("mundo_fb_oauth_state");
    return response;
  } catch (error) {
    return redirect("error:" + (error?.message || "Facebook rechazó la conexión."));
  }
}
