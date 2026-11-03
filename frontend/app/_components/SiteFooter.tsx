import Link from "next/link";
import { footerNav, site } from "../_content/site";

export default function SiteFooter() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto w-full max-w-[90rem] px-5 py-12 sm:px-8 lg:px-12">
        <div className="grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <p className="font-display text-heading font-semibold tracking-tight">
              <span aria-hidden className="mr-2 text-brand">§</span>
              {site.name}
            </p>
            <p className="mt-3 max-w-xs text-ui text-ink-muted">
              Finds the provisions of the GDPR that answer a question, cited to the official text.
            </p>
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 lg:col-span-7 lg:col-start-6">
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

        <div className="mt-10 flex flex-col gap-2 border-t border-rule pt-6 text-ui text-ink-muted sm:flex-row sm:justify-between">
          <p>
            © {new Date().getFullYear()} {site.name}. All rights reserved.
          </p>
          <p>Source text: {site.regulation}</p>
        </div>
      </div>
    </footer>
  );
}
