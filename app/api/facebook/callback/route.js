import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { saveFacebookAuthorization } from "../../../../lib/facebook";

export async function GET(request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const expectedState = cookies().get("mundo_fb_oauth_state")?.value;

  const site = process.env.NEXT_PUBLIC_SITE_URL || "https://mundo-al-dia-github-production.up.railway.app";
  const redirect = (message) =>
    NextResponse.redirect(new URL("/admin?facebook=" + encodeURIComponent(message), site));

  if (!code || !state || !expectedState || state !== expectedState) {
    return redirect("error");
  }

  try {
    const page = await saveFacebookAuthorization(code);
    const response = NextResponse.redirect(
      new URL("/admin?facebook=connected&name=" + encodeURIComponent(page.name), site)
    );
    response.cookies.delete("mundo_fb_oauth_state");
    return response;
  } catch (error) {
    return redirect("error:" + error.message);
  }
}
