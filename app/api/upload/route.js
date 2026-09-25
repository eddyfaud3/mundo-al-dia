import { v2 as cloudinary } from "cloudinary";
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { cookieName, validToken } from "../../../lib/auth";

export const runtime = "nodejs";

function getCloudinaryConfig() {
  const cloudinaryUrl = process.env.CLOUDINARY_URL?.trim();

  if (!cloudinaryUrl) {
    throw new Error("CLOUDINARY_URL no está configurada.");
  }

  // Let Cloudinary parse CLOUDINARY_URL itself. This handles encoded
  // credentials and Cloudinary URL formats more reliably than URL().
  cloudinary.config(cloudinaryUrl);
  const config = cloudinary.config();

  if (!config.cloud_name || !config.api_key || !config.api_secret) {
    throw new Error("CLOUDINARY_URL es inválida o está incompleta.");
  }

  return {
    cloudName: config.cloud_name,
    apiKey: config.api_key,
    apiSecret: config.api_secret,
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
      {
        timestamp,
        folder,
      },
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
      {
        error:
          error.message ||
          "No se pudo generar la firma de subida",
      },
      { status: 500 }
    );
  }
}
