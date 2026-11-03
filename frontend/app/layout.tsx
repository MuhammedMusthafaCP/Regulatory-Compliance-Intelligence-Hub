import type { Metadata } from "next";
import Link from "next/link";
import "@fontsource-variable/newsreader";
import "@fontsource-variable/public-sans";
import "./globals.css";
import SiteFooter from "./_components/SiteFooter";

export const metadata: Metadata = {
  title: { default: "Regulatory & Compliance Intelligence Hub", template: "%s · Regulatory & Compliance Intelligence Hub" },
  description:
    "Ask a plain-language question and get the GDPR provisions that answer it, each cited to its article, with an honest signal when the Regulation doesn't support an answer.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-paper font-ui text-ink antialiased selection:bg-foam">
        <header className="border-b border-rule">
          <div className="mx-auto flex w-full max-w-[90rem] items-center justify-between gap-6 px-5 py-4 sm:px-8 lg:px-12">
            <Link href="/" className="font-display text-heading font-semibold tracking-tight">
              <span aria-hidden className="mr-2 text-brand">§</span>
              Regulatory &amp; Compliance Intelligence Hub
            </Link>
            <nav aria-label="Primary" className="hidden items-center gap-8 text-ui md:flex">
              {[
                { label: "About", href: "/about" },
                { label: "How it works", href: "/about#how-it-works" },
                { label: "FAQ", href: "/faq" },
                { label: "Help", href: "/help" },
              ].map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="rounded-sm text-ink-soft underline decoration-transparent decoration-2 underline-offset-4 transition-colors hover:text-brand hover:decoration-lake focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                >
                  {l.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <div className="flex-1">{children}</div>

        <SiteFooter />
      </body>
    </html>
  );
}
