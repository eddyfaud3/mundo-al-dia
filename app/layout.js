import "./globals.css";
import "./mobile.css";

const siteUrl = "https://mundo-al-dia-github-production.up.railway.app";

export const metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Mundo al Día | Noticias internacionales y última hora",
    template: "%s | Mundo al Día"
  },
  description: "Las noticias más importantes de todo el mundo: actualidad internacional, última hora, información verificada, videos y reportajes en español.",
  applicationName: "Mundo al Día",
  keywords: [
    "Mundo al Día",
    "noticias internacionales",
    "última hora",
    "actualidad mundial",
    "noticias en español",
    "noticias del mundo"
  ],
  alternates: {
    canonical: "/"
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-touch-icon.svg"
  },
  openGraph: {
    type: "website",
    locale: "es_ES",
    siteName: "Mundo al Día",
    title: "Mundo al Día | Noticias internacionales y última hora",
    description: "Las noticias más importantes de todo el mundo, en español.",
    url: siteUrl
  },
  twitter: {
    card: "summary",
    title: "Mundo al Día | Noticias internacionales y última hora",
    description: "Las noticias más importantes de todo el mundo, en español."
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1
    }
  }
};

export default function RootLayout({ children }) {
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "NewsMediaOrganization",
    name: "Mundo al Día",
    url: siteUrl,
    description: "Medio digital de noticias internacionales y actualidad mundial en español.",
    email: "mundoaldia238@gmail.com",
    logo: {
      "@type": "ImageObject",
      url: `${siteUrl}/logo-mundo-al-dia.svg`
    },
    sameAs: []
  };

  return (
    <html lang="es">
      <body>
        {children}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema).replace(/</g, "\\u003c") }}
        />
      </body>
    </html>
  );
}
