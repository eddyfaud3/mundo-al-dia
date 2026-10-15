import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../lib/auth";
import { getInstagramConnection } from "../../../../lib/facebook";

export async function GET() {
  if (!validToken(cookies().get(cookieName)?.value)) {
    return NextResponse.json({ error: "No autorizado." }, { status: 401 });
  }
  try {
    const connection = await getInstagramConnection();
    return NextResponse.json({
      configured: true,
      connected: Boolean(connection),
      username: connection?.username || "",
      updatedAt: connection?.updatedAt || null,
    });
  } catch (error) {
    return NextResponse.json({ configured: true, connected: false, error: error?.message || "Error de Instagram." }, { status: 500 });
  }
}
