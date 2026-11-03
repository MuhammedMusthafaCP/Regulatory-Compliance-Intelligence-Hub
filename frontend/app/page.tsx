"use client";

import { forwardRef, useCallback, useEffect, useRef, useState } from "react";
import EnginePanel, { type EngineView } from "./EnginePanel";
import ResultView from "./ResultView";
import SearchForm from "./SearchForm";
import {
  getEngineState,
  MAX_QUESTION_LENGTH,
  restartEngine,
  searchGdpr,
  SearchApiError,
  type SearchResult,
} from "./api";

const POLL_INTERVAL_MS = 3000;
const MAX_POLLS = 40; // about two minutes; after that the user decides whether to try again

type View =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "done"; result: SearchResult }
  | { phase: "error"; question: string; error: SearchApiError };

const EXAMPLES = [
  "What is the right to be forgotten?",
  "How quickly must a data breach be reported to the authority?",
  "Does the GDPR apply to companies based outside the EU?",
];

const PRINCIPLES = [
  { title: "Finds the provisions", body: "Your question is matched against the Articles and Recitals of the Regulation." },
  { title: "Cites the article", body: "Each result quotes the text and names the Article it comes from, so you can check it." },
  { title: "Says when it can't", body: "If the Regulation doesn't support an answer, you get that signal instead of a guess." },
];

export default function SearchPage() {
  const [question, setQuestion] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [view, setView] = useState<View>({ phase: "idle" });
  const [engine, setEngine] = useState<EngineView>("loading");
  const [retrying, setRetrying] = useState(false);
  const [engineNote, setEngineNote] = useState<string | null>(null);
  const inflight = useRef<AbortController | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLHeadingElement>(null);

  // The engine loads in the background after the API starts: while it is "loading", poll its status. Polling is
  // bounded: after MAX_POLLS the page stops and lets the user decide, instead of asking forever.
  useEffect(() => {
    if (engine !== "loading") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let polls = 0;
    const check = async () => {
      try {
        const state = await getEngineState(controller.signal);
        if (state !== "loading") return setEngine(state);
        if (++polls >= MAX_POLLS) return setEngine("slow");
        timer = setTimeout(check, POLL_INTERVAL_MS);
      } catch (err) {
        if (!(err instanceof DOMException)) setEngine("unreachable");
      }
    };
    check();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [engine]);

  /** One user-initiated attempt. A failed engine is asked to start again (the server rate-limits this); the
   *  other states simply re-check. Nothing here repeats on its own. */
  const retryEngine = useCallback(async () => {
    setEngineNote(null);
    if (engine !== "failed") return setEngine("loading");
    setRetrying(true);
    try {
      const state = await restartEngine(new AbortController().signal);
      setEngine(state);
      if (state === "failed") setEngineNote("It was only just tried. Please wait about 30 seconds before trying again.");
    } catch {
      setEngine("unreachable");
    } finally {
      setRetrying(false);
    }
  }, [engine]);

  useEffect(() => () => inflight.current?.abort(), []);

  // Move focus to the results so keyboard and screen-reader users land on them.
  useEffect(() => {
    if (view.phase === "done") headingRef.current?.focus();
    if (view.phase === "error") errorRef.current?.focus();
  }, [view]);

  const run = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text) {
      setInputError("Enter a question to search.");
      return;
    }
    if (text.length > MAX_QUESTION_LENGTH) {
      setInputError(`Keep the question under ${MAX_QUESTION_LENGTH} characters.`);
      return;
    }
    setInputError(null);
    setQuestion(text);
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    setView({ phase: "loading" });
    try {
      const result = await searchGdpr(text, controller.signal);
      setView({ phase: "done", result });
    } catch (err) {
      if (err instanceof DOMException) return; // superseded by a newer search
      const error = err instanceof SearchApiError ? err : new SearchApiError("server", "Something went wrong on our side. Please try again.");
      // Engine problems are explained by the engine panel, not as a failed search.
      const engineProblem = { starting: "loading", not_configured: "not_configured", unavailable: "failed" } as const;
      if (error.kind in engineProblem) {
        setEngine(engineProblem[error.kind as keyof typeof engineProblem]);
        setView({ phase: "idle" });
        return;
      }
      setView({ phase: "error", question: text, error });
    }
  }, []);

  const searching = view.phase === "loading";
  const engineBlocked = engine === "not_configured" || engine === "failed" || engine === "slow";
  const engineStarting = engine === "loading";

  return (
    <main className="mx-auto w-full max-w-[90rem] px-5 pb-20 pt-10 sm:px-8 sm:pt-14 lg:px-12 lg:pt-16">
      <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-7">
          <p className="text-meta font-semibold uppercase text-brand">Regulation (EU) 2016/679</p>
          <h1 className="mt-3 max-w-3xl text-balance font-display text-display font-medium">What does the GDPR say?</h1>
          <p className="mt-4 max-w-2xl text-body text-ink-soft">
            Ask in plain language. Every result cites the article it comes from, and if the Regulation doesn&apos;t
            support an answer, you&apos;ll be told.
          </p>

          <div className="mt-8">
            <SearchForm
              value={question}
              onChange={(v) => {
                setQuestion(v);
                if (inputError) setInputError(null);
              }}
              onSubmit={() => run(question)}
              busy={searching}
              disabled={engineBlocked || engineStarting}
              disabledLabel={engineStarting ? "Starting…" : "Search"}
              error={inputError}
            />

            <EnginePanel engine={engine} retrying={retrying} note={engineNote} onRetry={retryEngine} />

            <div className="mt-4 text-ui text-ink-muted">
              <p className="text-meta font-semibold uppercase">Try</p>
              <ul className="mt-2 divide-y divide-rule border-y border-rule">
                {EXAMPLES.map((q) => (
                  <li key={q}>
                    <button
                      type="button"
                      disabled={searching || engineBlocked || engineStarting}
                      onClick={() => {
                        setQuestion(q);
                        run(q);
                      }}
                      className="group flex w-full items-center justify-between gap-4 py-3 text-left text-ink-soft transition-colors hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-60"
                    >
                      {q}
                      <span aria-hidden className="text-lake transition-transform group-hover:translate-x-1 group-disabled:translate-x-0">→</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <aside aria-labelledby="how-heading" className="lg:col-span-5 lg:pt-8">
          <div className="border border-rule bg-paper-raised p-6 sm:p-8">
            <h2 id="how-heading" className="text-meta font-semibold uppercase text-ink-muted">
              How every answer is built
            </h2>
            <ol className="mt-6 divide-y divide-rule">
              {PRINCIPLES.map((p, i) => (
                <li key={p.title} className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-3 py-5 first:pt-0 last:pb-0">
                  <span aria-hidden className="font-display text-title font-medium leading-none text-lake">
                    {i + 1}
                  </span>
                  <div>
                    <h3 className="font-display text-heading font-semibold">{p.title}</h3>
                    <p className="mt-1 text-ui text-ink-soft">{p.body}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-6 border-t border-rule pt-4 text-ui text-ink-muted">
              Quoted from the official text on EUR-Lex. Not legal advice.
            </p>
          </div>
        </aside>
      </div>

      <div aria-live="polite" aria-busy={searching}>
        {searching && <Progress />}
        {view.phase === "error" && (
          <ErrorPanel ref={errorRef} error={view.error} onRetry={() => run(view.question)} busy={searching} />
        )}
        {view.phase === "done" && <ResultView ref={headingRef} result={view.result} />}
      </div>
    </main>
  );
}

function Progress() {
  return (
    <div role="status" className="mt-10 border-t border-rule pt-6">
      <div className="h-0.5 overflow-hidden bg-rule">
        <div className="h-full w-1/3 bg-brand animate-sweep motion-reduce:w-full motion-reduce:animate-none motion-reduce:opacity-40" />
      </div>
      <p className="mt-3 text-ink-soft">Reading Regulation (EU) 2016/679… this usually takes a few seconds.</p>
    </div>
  );
}


const ErrorPanel = forwardRef<HTMLHeadingElement, { error: SearchApiError; onRetry: () => void; busy: boolean }>(
  function ErrorPanel({ error, onRetry, busy }, ref) {
    const canRetry = error.kind !== "invalid";
    return (
      <section aria-labelledby="error-heading" className="mt-10 border-l-4 border-signal-error bg-signal-errorbg px-5 py-4">
        <h2 id="error-heading" ref={ref} tabIndex={-1} className="font-semibold focus:outline-none">
          The search didn’t complete
        </h2>
        <p className="mt-1 text-ink-soft">{error.message}</p>
        {canRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={busy}
            className="mt-3 rounded-md border border-brand px-4 py-2 text-ui font-semibold text-brand hover:bg-brand hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:opacity-60"
          >
            Try again
          </button>
        )}
      </section>
    );
  },
);
