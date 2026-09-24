import "./globals.css";

export const metadata = {
  title: "Mundo al Día",
  description: "Las noticias más importantes del mundo, al día."
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
