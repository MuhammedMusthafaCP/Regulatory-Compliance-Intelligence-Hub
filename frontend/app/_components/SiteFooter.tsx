import Link from "next/link";
import { footerNav, site } from "../_content/site";

export default function SiteFooter() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_repeat(3,minmax(0,1fr))]">
          <div>
            <p className="font-display text-heading font-semibold tracking-tight">
              <span aria-hidden className="mr-2 text-brand">§</span>
              {site.name}
            </p>
            <p className="mt-3 max-w-xs text-ui text-ink-muted">
              Finds the provisions of the GDPR that answer a question, cited to the official text.
            </p>
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 lg:col-span-3">
            {footerNav.map((group) => (
              <div key={group.title}>
                <h2 className="text-meta font-semibold uppercase text-ink-muted">{group.title}</h2>
                <ul className="mt-3 space-y-2">
                  {group.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="rounded-sm text-ui text-ink-soft underline decoration-transparent decoration-2 underline-offset-4 transition-colors hover:text-brand hover:decoration-lake focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        <p className="mt-10 border-t border-rule pt-6 text-ui text-ink-muted">
          © {new Date().getFullYear()} {site.name}. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
