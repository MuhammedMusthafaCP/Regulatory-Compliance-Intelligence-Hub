import type { Metadata } from "next";
import Link from "next/link";
import "@fontsource-variable/newsreader";
import "@fontsource-variable/public-sans";

export const metadata: Metadata = {
  title: "Search the GDPR · Regulatory & Compliance Intelligence Hub",
  description:
    "Ask a plain-language question and get the GDPR provisions that answer it, each cited to its article, with an honest signal when the Regulation doesn't support an answer.",
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-theme="paper" className="flex min-h-screen flex-col bg-paper font-ui text-ink selection:bg-foam">
      <header className="border-b border-rule">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/search" className="font-display text-heading font-semibold tracking-tight">
            <span aria-hidden className="mr-2 text-brand">§</span>
            Regulatory &amp; Compliance Intelligence Hub
          </Link>
          <nav aria-label="Primary" className="shrink-0 text-ui">
            <Link href="/" className="text-ink-soft underline decoration-lake decoration-2 underline-offset-4 hover:text-brand">
              System status
            </Link>
          </nav>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-rule">
        <p className="mx-auto w-full max-w-6xl px-4 py-6 text-ui text-ink-muted sm:px-6 lg:px-8">
          Source: Regulation (EU) 2016/679 as published in the Official Journal on 4 May 2016 (EUR-Lex). Search results
          point to the text; they are not legal advice.
        </p>
      </footer>
    </div>
  );
}
