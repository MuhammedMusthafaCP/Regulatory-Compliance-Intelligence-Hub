/** Product facts and navigation shared by the footer and the information pages, so they cannot drift apart. */

const REPO = "https://github.com/MuhammedMusthafaCP/Regulatory-Compliance-Intelligence-Hub";

export const site = {
  name: "Regulatory & Compliance Intelligence Hub",
  regulation: "Regulation (EU) 2016/679",
  /** The official text the service quotes (EUR-Lex, English). */
  sourceUrl: "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679",
  repoUrl: REPO,
  issuesUrl: `${REPO}/issues`,
  /** Optional, set per deployment (frontend/.env.local). When unset, the Contact page does not show an email. */
  supportEmail: process.env.NEXT_PUBLIC_SUPPORT_EMAIL || null,
  /** Optional name of whoever runs this deployment. When unset, the pages say "the operator of this service". */
  operator: process.env.NEXT_PUBLIC_OPERATOR_NAME || null,
  /** Shown as "Last updated" on the legal pages; change it when their content changes. */
  documentsUpdated: "27 October 2026",
} as const;

export const operatorName = site.operator ?? "the operator of this service";

export interface NavLink {
  label: string;
  href: string;
}

export const footerNav: { title: string; links: NavLink[] }[] = [
  {
    title: "Product",
    links: [
      { label: "About", href: "/about" },
      { label: "How it works", href: "/about#how-it-works" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Terms and Conditions", href: "/terms" },
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Cookie Policy", href: "/cookies" },
      { label: "Disclaimer", href: "/disclaimer" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "FAQ", href: "/faq" },
      { label: "Help", href: "/help" },
      { label: "Contact", href: "/contact" },
    ],
  },
];
