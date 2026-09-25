import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../../lib/auth";
import { facebookConfigured, getFacebookConnection } from "../../../../lib/facebook";

export async function GET() {
  if (!validToken(cookies().get(cookieName)?.value)) {
    return NextResponse.json({error:"No autorizado."},{status:401});
  }
  if (!facebookConfigured()) {
    return NextResponse.json({configured:false,connected:false});
  }
  try {
    const connection = await getFacebookConnection();
    return NextResponse.json({
      configured:true,
      connected:Boolean(connection),
      pageName:connection?.pageName || "",
      updatedAt:connection?.updatedAt || null,
    });
  } catch (error) {
    return NextResponse.json({configured:true,connected:false,error:error.message});
  }
}
