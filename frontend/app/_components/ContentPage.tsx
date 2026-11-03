import Link from "next/link";
import type { ReactNode } from "react";
import PageNav from "./PageNav";

export const linkClass =
  "rounded-sm font-medium text-brand underline decoration-lake decoration-2 underline-offset-4 hover:text-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand";

/** Shared frame for the About, FAQ, Help, Contact and legal pages: one width, one type scale, one back link. */
export function ContentPage({
  title,
  intro,
  updated,
  children,
}: {
  title: string;
  intro?: ReactNode;
  updated?: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-[90rem] px-5 pb-20 pt-10 sm:px-8 sm:pt-14 lg:px-12 lg:pt-16">
      <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
        <header className="lg:col-span-4">
          <div className="lg:sticky lg:top-10">
            <Link href="/" className={`text-ui ${linkClass}`}>
              <span aria-hidden>← </span>Back to search
            </Link>
            <h1 className="mt-8 text-balance font-display text-display font-medium">{title}</h1>
            {intro && <p className="mt-5 text-body text-ink-soft">{intro}</p>}
            {updated && <p className="mt-3 text-ui text-ink-muted">Last updated {updated}</p>}
            <div className="mt-10 hidden border-t border-rule pt-8 lg:block">
              <PageNav />
            </div>
          </div>
        </header>

        <div className="space-y-12 lg:col-span-8 lg:border-l lg:border-rule lg:pl-16 [&>section+section]:border-t [&>section+section]:border-rule [&>section+section]:pt-12">
          {children}
        </div>
      </div>
    </main>
  );
}

export function Section({ id, title, children }: { id?: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6">
      <h2 className="font-display text-title font-medium">{title}</h2>
      <div className="mt-4 max-w-[72ch] space-y-4 text-body text-ink-soft">{children}</div>
    </section>
  );
}

export function Ul({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-2 pl-5 marker:text-lake">{children}</ul>;
}

export function Ol({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-2 pl-5 marker:font-semibold marker:text-brand">{children}</ol>;
}

export function ExtLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={linkClass}>
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function PageLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className={linkClass}>
      {children}
    </Link>
  );
}

/** A quiet aside for caveats that should not be missed. */
export function Callout({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <aside className="max-w-[68ch] border-l-4 border-lake bg-foam-soft px-4 py-3 text-ui text-ink-soft">
      {title && <p className="font-semibold text-ink">{title}</p>}
      <div className={title ? "mt-1 space-y-2" : "space-y-2"}>{children}</div>
    </aside>
  );
}

/** Term/description rows (no table, so nothing overflows on a phone). */
export function Facts({ children }: { children: ReactNode }) {
  return <dl className="divide-y divide-rule border-y border-rule">{children}</dl>;
}

export function Fact({ term, children }: { term: ReactNode; children: ReactNode }) {
  return (
    <div className="grid gap-1 py-4 sm:grid-cols-[13rem_minmax(0,1fr)] sm:gap-6">
      <dt className="font-semibold text-ink">{term}</dt>
      <dd className="space-y-2">{children}</dd>
    </div>
  );
}

/** Closing note for the legal pages: what the document is, and what it is not. */
export function LegalStatus() {
  return (
    <Callout title="Status of this document">
      <p>
        This page describes how the software behaves. It has not been reviewed by a lawyer for any particular
        jurisdiction, and it does not by itself guarantee compliance with any law. The operator of the service is
        responsible for confirming that it meets the requirements that apply to them before relying on it.
      </p>
    </Callout>
  );
}
