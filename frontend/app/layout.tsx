import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Regulatory & Compliance Intelligence Hub",
  description:
    "Enterprise AI platform for grounded, auditable regulatory compliance verification.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased text-slate-100">{children}</body>
    </html>
  );
}
