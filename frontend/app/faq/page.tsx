import type { Metadata } from "next";
import { ContentPage, ExtLink, PageLink } from "../_components/ContentPage";
import { Faq, type FaqItem } from "../_components/Faq";
import { site } from "../_content/site";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Answers to common questions about how the Hub works, where results come from, and what to do when search is unavailable.",
};

const items: FaqItem[] = [
  {
    id: "what-is-it",
    question: "What is the Regulatory & Compliance Intelligence Hub?",
    answer: (
      <p>
        A search service for {site.regulation}, the GDPR. You ask a question in plain language and it returns the
        provisions that answer it, each tied to its article, paragraph or point, and shows related recitals separately
        as context. It finds and quotes the official text; it does not write answers of its own.{" "}
        <PageLink href="/about">Read more about the Hub</PageLink>.
      </p>
    ),
  },
  {
    id: "how-search-works",
    question: "How does the search work?",
    answer: (
      <>
        <p>
          Your question is compared, by meaning and by keywords, with every provision of the Regulation’s articles.
          Everyday phrasing is mapped to the Regulation’s own wording. A second model then re-reads the best candidates
          against your exact question and sorts them. The score of the best match decides the label you see: supported,
          weak match, or no basis.
        </p>
        <p>
          <PageLink href="/about#how-it-works">See the step-by-step explanation</PageLink>.
        </p>
      </>
    ),
  },
  {
    id: "sources",
    question: "Where do the answers and citations come from?",
    answer: (
      <p>
        Every result is a quotation from the English text of {site.regulation} as published in the Official Journal of
        the European Union on 4 May 2016, taken from <ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink>. Each result
        shows its citation (for example Article 17(1)) and a link to that passage. This copy is the original 2016 text
        and may not include later corrections; the Official Journal is the authoritative source.
      </p>
    ),
  },
  {
    id: "verify",
    question: "How can I verify a cited article?",
    answer: (
      <>
        <p>
          Choose “Read on EUR-Lex” under a result. It opens that passage in the official text, in a new tab. Compare
          the wording and the citation.
        </p>
        <p>
          For anything that matters, also read the neighbouring provisions and the version in the Official Journal; a
          single paragraph rarely tells the whole story.
        </p>
      </>
    ),
  },
  {
    id: "no-answer",
    question: "What happens when the system can’t find a relevant answer?",
    answer: (
      <>
        <p>
          You will see “No basis in the GDPR” and no provisions. The service chooses to say so rather than show
          provisions that don’t really answer the question.
        </p>
        <p>
          This usually means the question is not about the GDPR (tax or employment law, for example), or that it asks
          for something the Regulation does not settle, such as a specific retention period. Try rephrasing with the
          Regulation’s terms; <PageLink href="/help">Help</PageLink> has tips.
        </p>
      </>
    ),
  },
  {
    id: "why-search-fails",
    question: "Why might a search fail?",
    answer: (
      <>
        <p>
          The service may still be starting (wait a few seconds), too many searches may be running at once (try again
          shortly), a search may take too long, your connection to the service may drop, or the service may be
          temporarily unavailable. The message tells you which, and{" "}
          <PageLink href="/help#when-something-goes-wrong">Help</PageLink> explains what to do in each case.
        </p>
        <p>A failure is never a statement about the law: it only means no result could be produced.</p>
      </>
    ),
  },
  {
    id: "engine-unavailable",
    question: "What does it mean when the search engine is unavailable?",
    answer: (
      <>
        <p>
          <strong className="text-ink">“Search is currently unavailable”</strong> means the search service has not been
          configured on this server. Only its administrator can change that, so please{" "}
          <PageLink href="/contact">get in touch</PageLink>.
        </p>
        <p>
          <strong className="text-ink">“Search is temporarily unavailable”</strong> means it is configured but could
          not start. This is usually temporary: use “Try again” after a short wait, and contact support if it persists.
        </p>
      </>
    ),
  },
  {
    id: "legal-advice",
    question: "Is the information legal advice?",
    answer: (
      <p>
        No. The Hub helps you locate and read regulatory text. It does not consider your facts, your jurisdiction or
        your circumstances, and its results can be incomplete or ranked imperfectly. For decisions that matter, read
        the authoritative text and take advice from a qualified professional. See the{" "}
        <PageLink href="/disclaimer">Disclaimer</PageLink>.
      </p>
    ),
  },
  {
    id: "query-data",
    question: "How is my query data handled?",
    answer: (
      <>
        <p>
          Your question is used only to run your search. The application does not store it, does not write it to its
          logs, and does not send it to a third-party AI or search service; it is processed in memory on the service’s
          own servers. The servers may keep ordinary request logs (time, page requested, status and network address),
          which are controlled by whoever runs the service.
        </p>
        <p>
          Please don’t put personal or confidential information in a question.{" "}
          <PageLink href="/privacy">Read the Privacy Policy</PageLink>.
        </p>
      </>
    ),
  },
  {
    id: "coverage",
    question: "Which regulations does it cover?",
    answer: (
      <p>
        Only the GDPR today: its 99 articles and 173 recitals. Other regulations, documents you upload and your own
        policies are not covered.
      </p>
    ),
  },
  {
    id: "result-labels",
    question: "What do “supported”, “weak match” and “recitals” mean?",
    answer: (
      <>
        <p>
          <strong className="text-ink">Supported by the Regulation:</strong> the best provisions closely match your
          question. <strong className="text-ink">Weak match:</strong> the closest provisions only loosely match; read
          them with caution. <strong className="text-ink">No basis:</strong> nothing in the GDPR supports an answer.
          These labels come from a relevance score, not a legal judgement.
        </p>
        <p>
          <strong className="text-ink">Provisions</strong> are the operative text of the articles.{" "}
          <strong className="text-ink">Recitals</strong> explain the purpose of the rules; they help interpretation but
          are not binding.
        </p>
      </>
    ),
  },
  {
    id: "report-problem",
    question: "How can I report a problem or request assistance?",
    answer: (
      <p>
        Use the <PageLink href="/contact">Contact page</PageLink>. It explains how to report a problem or ask for help
        and what to include: the message you saw, roughly when, and the question if it isn’t sensitive.
      </p>
    ),
  },
];

export default function FaqPage() {
  return (
    <ContentPage
      title="Frequently asked questions"
      intro="Short answers about how the Hub works, where its results come from, and what to do when something goes wrong."
    >
      <Faq items={items} />
      <p className="max-w-[68ch] text-body text-ink-soft">
        Didn’t find what you need? Try <PageLink href="/help">Help</PageLink> or <PageLink href="/contact">Contact</PageLink>.
      </p>
    </ContentPage>
  );
}
