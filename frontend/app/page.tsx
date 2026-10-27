"use client";

import { forwardRef, useCallback, useEffect, useRef, useState } from "react";
import ResultView from "./ResultView";
import SearchForm from "./SearchForm";
import {
  getEngineState,
  MAX_QUESTION_LENGTH,
  searchGdpr,
  SearchApiError,
  type EngineState,
  type SearchResult,
} from "./api";

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

export default function SearchPage() {
  const [question, setQuestion] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [view, setView] = useState<View>({ phase: "idle" });
  const [engine, setEngine] = useState<EngineState | "unreachable">("loading");
  const inflight = useRef<AbortController | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLHeadingElement>(null);

  // The engine loads in the background after the API starts: while it is "loading" (on first visit, or after a
  // search was told it is starting), poll until it is ready.
  useEffect(() => {
    if (engine !== "loading") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const check = async () => {
      try {
        const state = await getEngineState(controller.signal);
        setEngine(state);
        if (state === "loading") timer = setTimeout(check, 3000);
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
      const error = err instanceof SearchApiError ? err : new SearchApiError("server", "The search could not be completed. Please try again.");
      if (error.kind === "starting") setEngine("loading");
      setView({ phase: "error", question: text, error });
    }
  }, []);

  const searching = view.phase === "loading";
  const engineBlocked = engine === "unavailable" || engine === "failed";
  const engineStarting = engine === "loading";

  return (
    <main className="mx-auto w-full max-w-6xl px-4 pb-20 pt-10 sm:px-6 sm:pt-14 lg:px-8">
      <p className="text-meta font-semibold uppercase text-brand">Regulation (EU) 2016/679</p>
      <h1 className="mt-3 max-w-3xl text-balance font-display text-display font-medium">What does the GDPR say?</h1>
      <p className="mt-4 max-w-2xl text-body text-ink-soft">
        Ask in plain language. Every result cites the article it comes from, and if the Regulation doesn&apos;t support an
        answer, you&apos;ll be told.
      </p>

      <div className="mt-8 max-w-3xl">
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

        <EngineNotice engine={engine} />

        <div className="mt-3 text-ui text-ink-muted">
          <p>Try</p>
          <ul className="mt-1 flex flex-col gap-1">
            {EXAMPLES.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  disabled={searching || engineBlocked || engineStarting}
                  onClick={() => {
                    setQuestion(q);
                    run(q);
                  }}
                  className="text-left text-ink-soft underline decoration-lake decoration-2 underline-offset-4 hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:no-underline disabled:opacity-60"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
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

function EngineNotice({ engine }: { engine: EngineState | "unreachable" }) {
  const text =
    engine === "loading"
      ? "The search engine is starting up. This takes a few seconds, and the search button will enable itself when it is ready."
      : engine === "unavailable"
        ? "Search is not available on this server. It needs the optional search dependencies; see the README."
        : engine === "failed"
          ? "The search engine failed to start. Check the backend logs."
          : engine === "unreachable"
            ? "Can't reach the backend. Check that it is running; you can still try a search."
            : null;
  if (!text) return null;
  return (
    <p role="status" className="mt-1 border-l-4 border-signal-weak bg-signal-weakbg px-4 py-3 text-ui">
      {text}
    </p>
  );
}

function Progress() {
  return (
    <div role="status" className="mt-10 max-w-3xl border-t border-rule pt-6">
      <div className="h-0.5 overflow-hidden bg-rule">
        <div className="h-full w-1/3 bg-brand animate-sweep motion-reduce:w-full motion-reduce:animate-none motion-reduce:opacity-40" />
      </div>
      <p className="mt-3 text-ink-soft">Reading Regulation (EU) 2016/679… this usually takes a few seconds.</p>
    </div>
  );
}


const ErrorPanel = forwardRef<HTMLHeadingElement, { error: SearchApiError; onRetry: () => void; busy: boolean }>(
  function ErrorPanel({ error, onRetry, busy }, ref) {
    const canRetry = error.kind !== "unavailable" && error.kind !== "invalid";
    return (
      <section aria-labelledby="error-heading" className="mt-10 max-w-3xl border-l-4 border-signal-error bg-signal-errorbg px-5 py-4">
        <h2 id="error-heading" ref={ref} tabIndex={-1} className="font-semibold focus:outline-none">
          {error.kind === "starting" ? "The search engine is still starting" : "The search didn’t complete"}
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
