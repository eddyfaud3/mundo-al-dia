import { v2 as cloudinary } from "cloudinary";
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../lib/auth";

export const runtime = "nodejs";

function getCloudinaryConfig() {
  const cloudName = process.env.CLOUDINARY_CLOUD_NAME?.trim();
  const apiKey = process.env.CLOUDINARY_API_KEY?.trim();
  const apiSecret = process.env.CLOUDINARY_API_SECRET?.trim();

  if (cloudName && apiKey && apiSecret) {
    return { cloudName, apiKey, apiSecret };
  }

  let value = process.env.CLOUDINARY_URL?.trim();

  if (!value) {
    throw new Error("Falta la configuración de Cloudinary. En Railway agrega CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET.");
  }

  value = value.replace(/^CLOUDINARY_URL\s*=\s*/i, "").trim();
  value = value.replace(/^['"]|['"]$/g, "").trim();

  if (value.toLowerCase().startsWith("cloudinary://")) {
    value = value.slice("cloudinary://".length);
  }

  const at = value.lastIndexOf("@");
  const colon = value.indexOf(":");

  if (colon <= 0 || at <= colon + 1 || at === value.length - 1) {
    throw new Error("La configuración de Cloudinary no es válida. Usa las tres variables separadas en Railway.");
  }

  const parsedApiKey = value.slice(0, colon).trim();
  const parsedApiSecret = value.slice(colon + 1, at).trim();
  const parsedCloudName = value.slice(at + 1).trim().replace(/\/$/, "");

  if (!parsedApiKey || !parsedApiSecret || !parsedCloudName) {
    throw new Error("La configuración de Cloudinary está incompleta. Usa las tres variables separadas en Railway.");
  }

  return {
    cloudName: decodeURIComponent(parsedCloudName),
    apiKey: decodeURIComponent(parsedApiKey),
    apiSecret: decodeURIComponent(parsedApiSecret),
  };
}

export async function POST() {
  try {
    const token = (await cookies()).get(cookieName)?.value;
    if (!validToken(token)) {
      return NextResponse.json({ error: "No autorizado." }, { status: 401 });
    }

    const config = getCloudinaryConfig();

    cloudinary.config({
      cloud_name: config.cloudName,
      api_key: config.apiKey,
      api_secret: config.apiSecret,
    });

    const timestamp = Math.round(Date.now() / 1000);
    const folder = "mundo-al-dia";

    const signature = cloudinary.utils.api_sign_request(
      { timestamp, folder },
      config.apiSecret
    );

    return NextResponse.json({
      timestamp,
      signature,
      cloudName: config.cloudName,
      apiKey: config.apiKey,
      folder,
    });
  } catch (error) {
    console.error("Error Cloudinary:", error);
    return NextResponse.json(
      { error: error.message || "No se pudo generar la firma de subida" },
      { status: 500 }
    );
  }
}
