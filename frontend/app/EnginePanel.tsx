import Link from "next/link";
import type { EngineState } from "./api";

/** "unreachable": the backend didn't answer. "slow": still starting after the polling limit. */
export type EngineView = EngineState | "unreachable" | "slow";

const link =
  "rounded-sm font-medium text-brand underline decoration-lake decoration-2 underline-offset-4 hover:text-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand";

const COPY: Record<"not_configured" | "failed" | "unreachable" | "slow", { title: string; body: string; tone: string; retry: boolean }> = {
  not_configured: {
    title: "Search is currently unavailable",
    body: "The search service has not been configured yet. Please try again later or contact the application administrator if you need assistance.",
    tone: "border-ink-muted bg-paper-sunk",
    retry: false,
  },
  failed: {
    title: "Search is temporarily unavailable",
    body: "We couldn’t start the search service. This is usually temporary, so please try again in a few minutes.",
    tone: "border-signal-weak bg-signal-weakbg",
    retry: true,
  },
  slow: {
    title: "Search is taking longer than expected to start",
    body: "The service is still starting. You can wait a little longer and try again.",
    tone: "border-signal-weak bg-signal-weakbg",
    retry: true,
  },
  unreachable: {
    title: "We can’t reach the search service",
    body: "Check your internet connection and try again. If the problem continues, the service may be down for maintenance.",
    tone: "border-signal-weak bg-signal-weakbg",
    retry: true,
  },
};

export default function EnginePanel({
  engine,
  retrying,
  note,
  onRetry,
}: {
  engine: EngineView;
  retrying: boolean;
  note: string | null;
  onRetry: () => void;
}) {
  if (engine === "ready") return null;

  if (engine === "loading") {
    return (
      <p role="status" className="mt-1 border-l-4 border-signal-weak bg-signal-weakbg px-4 py-3 text-ui">
        Search is starting up. This takes a few seconds, and the Search button will enable itself when it is ready.
      </p>
    );
  }

  const copy = COPY[engine];
  return (
    <section role="status" aria-labelledby="engine-title" className={`mt-1 border-l-4 px-5 py-4 ${copy.tone}`}>
      <h2 id="engine-title" className="font-semibold">{copy.title}</h2>
      <p className="mt-1 text-ink-soft">{copy.body}</p>
      {copy.retry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="mt-3 rounded-md border border-brand px-4 py-2 text-ui font-semibold text-brand hover:bg-brand hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:cursor-not-allowed disabled:opacity-60"
        >
          {retrying ? "Trying…" : "Try again"}
        </button>
      )}
      {note && <p className="mt-2 text-ui text-ink-muted">{note}</p>}
      <p className="mt-3 text-ui text-ink-soft">
        Need help? <Link href="/contact" className={link}>Contact support</Link> or read the{" "}
        <Link href="/faq#engine-unavailable" className={link}>FAQ</Link>.
      </p>
    </section>
  );
}
