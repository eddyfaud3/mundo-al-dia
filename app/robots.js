const baseUrl = "https://mundo-al-dia-github-production.up.railway.app";

export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin", "/api/admin"]
    },
    sitemap: `${baseUrl}/sitemap.xml`
  };
}
