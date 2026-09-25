import crypto from "crypto";

const COOKIE = "mundo_admin";

function secret() {
  return process.env.ADMIN_PASSWORD || "";
}

export function isConfigured() {
  return Boolean(secret());
}

function sign(value) {
  return crypto.createHmac("sha256", secret()).update(value).digest("hex");
}

export function makeToken() {
  const value = `admin:${Date.now()}`;
  return `${value}.${sign(value)}`;
}

export function validToken(token) {
  if (!token || !secret()) return false;
  const [value, signature] = token.split(".");
  if (!value || !signature) return false;
  const expected = sign(value);
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}

export const cookieName = COOKIE;
