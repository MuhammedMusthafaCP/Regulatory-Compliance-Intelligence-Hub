"use client";

import { forwardRef, useId, useState } from "react";
import { eurLexUrl, type ContextRecital, type EvidenceStatus, type Provision, type SearchResult } from "./api";

const VERDICT: Record<EvidenceStatus, { title: string; detail: string; tone: string }> = {
  supported: {
    title: "Supported by the Regulation",
    detail: "These provisions directly address your question.",
    tone: "border-brand bg-foam-soft",
  },
  weak_evidence: {
    title: "Weak match: read with caution",
    detail: "The closest provisions only weakly match and may not answer your question directly.",
    tone: "border-signal-weak bg-signal-weakbg",
  },
  no_basis: {
    title: "No basis in the GDPR",
    detail:
      "Nothing in Regulation (EU) 2016/679 supports an answer to this question. If it is about data protection, try rephrasing with terms from the Regulation such as “controller”, “data subject” or a specific article.",
    tone: "border-ink-muted bg-paper-sunk",
  },
};

const ResultView = forwardRef<HTMLHeadingElement, { result: SearchResult }>(function ResultView({ result }, headingRef) {
  const verdict = VERDICT[result.status];
  const hasContext = result.context.length > 0;

  return (
    <section aria-labelledby="results-heading" className="mt-10 border-t border-rule pt-8">
      <p className="text-meta font-semibold uppercase text-ink-muted">Results for</p>
      <h2 id="results-heading" ref={headingRef} tabIndex={-1} className="mt-1 max-w-3xl text-balance font-display text-title font-medium focus:outline-none">
        {result.question}
      </h2>

      <div className={`mt-5 max-w-3xl border-l-4 px-5 py-4 ${verdict.tone}`}>
        <p className="font-semibold">{verdict.title}</p>
        <p className="mt-1 text-ink-soft">{verdict.detail}</p>
        <p className="mt-2 text-ui text-ink-muted">
          <span title="How well the best provision matches the question, from 0 to 1. A relative signal, not a probability.">
            Match score {result.confidence.toFixed(3)}
          </span>{" "}
          · {(result.took_ms / 1000).toFixed(1)} s
        </p>
      </div>

      {result.provisions.length > 0 && (
        <div className={`mt-10 gap-12 ${hasContext ? "lg:grid lg:grid-cols-[minmax(0,1fr)_21rem]" : ""}`}>
          <div>
            <h3 className="text-meta font-semibold uppercase text-ink-muted">
              {result.provisions.length === 1 ? "Provision" : `${result.provisions.length} provisions`} · the operative text
            </h3>
            <ol className="mt-2">
              {result.provisions.map((p, i) => (
                <ProvisionItem key={p.chunk_id} provision={p} rank={i + 1} />
              ))}
            </ol>
          </div>

          {hasContext && (
            <aside aria-labelledby="context-heading" className="mt-12 lg:mt-0">
              <div className="lg:sticky lg:top-6">
                <h3 id="context-heading" className="text-meta font-semibold uppercase text-ink-muted">
                  Recitals · interpretive context
                </h3>
                <p className="mt-2 text-ui text-ink-muted">
                  Recitals explain the purpose of the Regulation. They are not binding; the provisions are.
                </p>
                <ul className="mt-5 space-y-6">
                  {result.context.map((c) => (
                    <RecitalItem key={c.chunk_id} recital={c} />
                  ))}
                </ul>
              </div>
            </aside>
          )}
        </div>
      )}
    </section>
  );
});

export default ResultView;

function ProvisionItem({ provision: p, rank }: { provision: Provision; rank: number }) {
  return (
    <li className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-2 border-t border-rule py-7 first:border-t-0 sm:grid-cols-[3rem_minmax(0,1fr)]">
      <span aria-hidden className="font-display text-title leading-none text-lake">{rank}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h4 className="font-display text-heading font-semibold">{p.citation}</h4>
          <p className="text-meta uppercase text-ink-muted">{p.article_title}</p>
        </div>
        <ClampedText text={p.text} className="mt-3 max-w-[68ch]" />
        <SourceLink url={p.source_url} />
      </div>
    </li>
  );
}

function RecitalItem({ recital: r }: { recital: ContextRecital }) {
  return (
    <li className="border-l-2 border-lake pl-4">
      <h4 className="font-display text-heading font-semibold">{r.citation}</h4>
      <ClampedText text={r.text} small className="mt-1 text-ink-soft" />
      <SourceLink url={r.source_url} />
    </li>
  );
}

function SourceLink({ url }: { url: string | null }) {
  const href = eurLexUrl(url);
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 inline-block text-ui font-medium text-brand underline decoration-lake decoration-2 underline-offset-4 hover:text-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
    >
      Read on EUR-Lex<span className="sr-only"> (opens in a new tab)</span> ↗
    </a>
  );
}

function ClampedText({ text, className = "", small = false }: { text: string; className?: string; small?: boolean }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const long = text.length > (small ? 340 : 560);
  const clamp = long && !open ? (small ? "line-clamp-5" : "line-clamp-6") : "";

  return (
    <div className={className}>
      <p id={id} className={`whitespace-pre-line ${small ? "text-ui" : "text-body"} ${clamp}`}>
        {text}
      </p>
      {long && (
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((v) => !v)}
          className="mt-1 text-ui font-medium text-brand underline decoration-lake decoration-2 underline-offset-4 hover:text-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
        >
          {open ? "Show less" : "Show full text"}
        </button>
      )}
    </div>
  );
}
