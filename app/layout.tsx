import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Homeless — ApartmentAgent",
  description: "An H Company computer-use agent finds and contacts apartments for you.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
