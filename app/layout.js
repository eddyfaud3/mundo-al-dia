import "./globals.css";

export const metadata = {
  metadataBase: new URL("https://mundo-al-dia-github-production.up.railway.app"),
  title: {
    default: "Mundo al Día",
    template: "%s | Mundo al Día"
  },
  description: "Las noticias más importantes del mundo, al día.",
  applicationName: "Mundo al Día",
  openGraph: {
    type: "website",
    locale: "es_ES",
    siteName: "Mundo al Día",
    title: "Mundo al Día",
    description: "Las noticias más importantes del mundo, al día.",
    url: "/"
  },
  twitter: {
    card: "summary_large_image",
    title: "Mundo al Día",
    description: "Las noticias más importantes del mundo, al día."
  },
  robots: {
    index: true,
    follow: true
  }
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
