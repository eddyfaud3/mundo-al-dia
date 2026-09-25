import { NextResponse } from "next/server";
import { isConfigured, makeToken, cookieName } from "../../../../lib/auth";

export async function POST(request) {
  try {
    const { password } = await request.json();
    if (!isConfigured()) {
      return NextResponse.json({error:"ADMIN_PASSWORD todavía no está configurada en Railway."},{status:503});
    }
    if (password !== process.env.ADMIN_PASSWORD) {
      return NextResponse.json({error:"Contraseña incorrecta."},{status:401});
    }
    const response = NextResponse.json({ok:true});
    response.cookies.set(cookieName, makeToken(), {
      httpOnly:true, secure:true, sameSite:"lax", path:"/", maxAge:60*60*24*7
    });
    return response;
  } catch {
    return NextResponse.json({error:"Solicitud no válida."},{status:400});
  }
}
