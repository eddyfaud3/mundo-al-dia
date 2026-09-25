import crypto from "crypto";
import { getPool } from "./db";

const VERSION = process.env.META_GRAPH_VERSION || "v26.0";

function appConfig() {
  return {
    appId: process.env.META_APP_ID || "",
    appSecret: process.env.META_APP_SECRET || "",
    redirectUri:
      process.env.META_REDIRECT_URI ||
      "https://mundo-al-dia-github-production.up.railway.app/api/facebook/callback",
    pageId: process.env.META_PAGE_ID || "",
  };
}

function encryptionKey() {
  const secret = process.env.ADMIN_PASSWORD || "";
  if (!secret) throw new Error("ADMIN_PASSWORD no está configurada.");
  return crypto.createHash("sha256").update(secret).digest();
}

function encrypt(value) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", encryptionKey(), iv);
  const encrypted = Buffer.concat([cipher.update(value, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv, tag, encrypted].map((part) => part.toString("base64url")).join(".");
}

function decrypt(value) {
  const [ivText, tagText, encryptedText] = String(value || "").split(".");
  if (!ivText || !tagText || !encryptedText) throw new Error("Token de Facebook inválido.");
  const decipher = crypto.createDecipheriv(
    "aes-256-gcm",
    encryptionKey(),
    Buffer.from(ivText, "base64url")
  );
  decipher.setAuthTag(Buffer.from(tagText, "base64url"));
  return Buffer.concat([
    decipher.update(Buffer.from(encryptedText, "base64url")),
    decipher.final(),
  ]).toString("utf8");
}

export function getFacebookConfig() {
  return appConfig();
}

export function facebookConfigured() {
  const { appId, appSecret, redirectUri } = appConfig();
  return Boolean(appId && appSecret && redirectUri);
}

export function facebookLoginUrl(state) {
  const { appId, redirectUri } = appConfig();
  if (!appId || !redirectUri) throw new Error("META_APP_ID o META_REDIRECT_URI no están configurados.");
  const params = new URLSearchParams({
    client_id: appId,
    redirect_uri: redirectUri,
    state,
    response_type: "code",
    scope: "pages_show_list,pages_read_engagement,pages_manage_posts",
  });
  return `https://www.facebook.com/${VERSION}/dialog/oauth?${params.toString()}`;
}

async function graph(path, options = {}) {
  const response = await fetch(`https://graph.facebook.com/${VERSION}${path}`, {
    ...options,
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    throw new Error(data.error?.message || "Facebook Graph API devolvió un error.");
  }
  return data;
}

export async function saveFacebookAuthorization(code) {
  const { appId, appSecret, redirectUri, pageId } = appConfig();
  if (!appId || !appSecret || !redirectUri) {
    throw new Error("Faltan META_APP_ID, META_APP_SECRET o META_REDIRECT_URI en Railway.");
  }

  const tokenParams = new URLSearchParams({
    client_id: appId,
    client_secret: appSecret,
    redirect_uri: redirectUri,
    code,
  });
  const userToken = await graph(`/oauth/access_token?${tokenParams.toString()}`);
  const pages = await graph(
    `/me/accounts?fields=id,name,access_token,tasks&access_token=${encodeURIComponent(userToken.access_token)}`
  );

  if (!pages.data?.length) {
    throw new Error("Facebook no devolvió ninguna página administrada por esta cuenta.");
  }

  const page =
    (pageId && pages.data.find((item) => String(item.id) === String(pageId))) ||
    pages.data[0];

  if (!page?.access_token) {
    throw new Error("No se pudo obtener el Page Access Token.");
  }

  const db = getPool();
  await db.query(`
    CREATE TABLE IF NOT EXISTS social_connections (
      provider TEXT PRIMARY KEY,
      page_id TEXT NOT NULL,
      page_name TEXT NOT NULL,
      encrypted_token TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await db.query(
    `INSERT INTO social_connections (provider,page_id,page_name,encrypted_token,updated_at)
     VALUES ('facebook',$1,$2,$3,NOW())
     ON CONFLICT (provider) DO UPDATE SET
       page_id=EXCLUDED.page_id,
       page_name=EXCLUDED.page_name,
       encrypted_token=EXCLUDED.encrypted_token,
       updated_at=NOW()`,
    [page.id, page.name, encrypt(page.access_token)]
  );

  return { id: page.id, name: page.name };
}

export async function getFacebookConnection() {
  const db = getPool();
  await db.query(`
    CREATE TABLE IF NOT EXISTS social_connections (
      provider TEXT PRIMARY KEY,
      page_id TEXT NOT NULL,
      page_name TEXT NOT NULL,
      encrypted_token TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);
  const { rows } = await db.query(
    "SELECT page_id,page_name,encrypted_token,updated_at FROM social_connections WHERE provider='facebook' LIMIT 1"
  );
  if (!rows[0]) return null;
  return {
    pageId: rows[0].page_id,
    pageName: rows[0].page_name,
    token: decrypt(rows[0].encrypted_token),
    updatedAt: rows[0].updated_at,
  };
}

export async function disconnectFacebook() {
  const db = getPool();
  await db.query("DELETE FROM social_connections WHERE provider='facebook'");
}

export async function publishArticleToFacebook(article) {
  const connection = await getFacebookConnection();
  if (!connection) return { published: false, reason: "Facebook no está conectado." };

  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL ||
    "https://mundo-al-dia-github-production.up.railway.app";
  const link = `${siteUrl}/noticia/${encodeURIComponent(article.slug)}`;
  const message = [
    `📰 ${article.title}`,
    article.excerpt ? article.excerpt.trim() : "",
    "Lee la noticia completa en Mundo al Día.",
  ]
    .filter(Boolean)
    .join("\n\n");

  const body = new URLSearchParams({
    message,
    link,
    access_token: connection.token,
  });

  const result = await graph(`/${connection.pageId}/feed`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  return { published: true, postId: result.id, pageName: connection.pageName };
}
