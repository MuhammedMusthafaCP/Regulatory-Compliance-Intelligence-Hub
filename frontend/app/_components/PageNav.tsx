"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { footerNav } from "../_content/site";

/** Sibling pages for the information pages' side column; the current page is marked for assistive tech too. */
export default function PageNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Information pages" className="space-y-6">
      {footerNav.map((group) => {
        const links = group.links.filter((l) => !l.href.includes("#"));
        return (
          <div key={group.title}>
            <h2 className="text-meta font-semibold uppercase text-ink-muted">{group.title}</h2>
            <ul className="mt-2 border-l border-rule">
              {links.map((l) => {
                const current = pathname === l.href;
                return (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      aria-current={current ? "page" : undefined}
                      className={`-ml-px block border-l-2 py-1.5 pl-4 text-ui transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                        current
                          ? "border-brand font-semibold text-brand"
                          : "border-transparent text-ink-soft hover:border-lake hover:text-brand"
                      }`}
                    >
                      {l.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
