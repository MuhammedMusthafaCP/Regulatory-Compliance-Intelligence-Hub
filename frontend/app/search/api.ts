import { z } from "zod";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7001";
export const MAX_QUESTION_LENGTH = 500;
const CLIENT_TIMEOUT_MS = 75_000; // longer than the server's own 60 s limit, so the server answers first

const sourceUrl = z.string().nullable();

const ProvisionSchema = z.object({
  role: z.literal("operative"),
  citation: z.string(),
  article: z.number(),
  article_title: z.string(),
  text: z.string(),
  score: z.number(),
  chunk_id: z.string(),
  source_url: sourceUrl,
});

const ContextRecitalSchema = z.object({
  role: z.literal("interpretive_context"),
  citation: z.string(),
  text: z.string(),
  score: z.number(),
  relevance: z.number(),
  chunk_id: z.string(),
  source_url: sourceUrl,
});

const SearchResultSchema = z.object({
  question: z.string(),
  status: z.enum(["supported", "weak_evidence", "no_basis"]),
  confidence: z.number(),
  note: z.string().nullable(),
  provisions: z.array(ProvisionSchema),
  context: z.array(ContextRecitalSchema),
  took_ms: z.number(),
});

const EngineStatusSchema = z.object({ state: z.enum(["loading", "ready", "unavailable", "failed"]) });

export type Provision = z.infer<typeof ProvisionSchema>;
export type ContextRecital = z.infer<typeof ContextRecitalSchema>;
export type SearchResult = z.infer<typeof SearchResultSchema>;
export type EvidenceStatus = SearchResult["status"];
export type EngineState = z.infer<typeof EngineStatusSchema>["state"];

/** Only EUR-Lex links are rendered as links; anything else from the API is ignored. */
export function eurLexUrl(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.protocol === "https:" && url.hostname === "eur-lex.europa.eu" ? url.href : null;
  } catch {
    return null;
  }
}

export type SearchErrorKind = "invalid" | "starting" | "unavailable" | "busy" | "timeout" | "server" | "network";

export class SearchApiError extends Error {
  constructor(readonly kind: SearchErrorKind, message: string) {
    super(message);
    this.name = "SearchApiError";
  }
}

const DEFAULT_MESSAGES: Record<SearchErrorKind, string> = {
  invalid: `Enter a question of 1 to ${MAX_QUESTION_LENGTH} characters.`,
  starting: "The search engine is starting up. Please try again in a few seconds.",
  unavailable: "Search is not available on this server.",
  busy: "The search engine is busy. Please try again shortly.",
  timeout: "The search took too long. Please try again.",
  server: "The search could not be completed. Please try again.",
  network: "Can't reach the search service. Check that the backend is running, then try again.",
};

const KIND_BY_CODE: Record<string, SearchErrorKind> = {
  search_loading: "starting",
  search_unavailable: "unavailable",
  search_busy: "busy",
  search_timeout: "timeout",
};

async function request<T>(path: string, schema: z.ZodType<T>, init: RequestInit & { signal: AbortSignal }): Promise<T> {
  const signal = typeof AbortSignal.any === "function" ? AbortSignal.any([init.signal, AbortSignal.timeout(CLIENT_TIMEOUT_MS)]) : init.signal;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    if (err instanceof DOMException && err.name === "TimeoutError") throw new SearchApiError("timeout", DEFAULT_MESSAGES.timeout);
    throw new SearchApiError("network", DEFAULT_MESSAGES.network);
  }

  if (res.ok) {
    const parsed = schema.safeParse(await res.json().catch(() => null));
    if (!parsed.success) throw new SearchApiError("server", DEFAULT_MESSAGES.server); // unexpected payload shape
    return parsed.data;
  }

  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  const code: string | undefined = typeof detail === "object" && !Array.isArray(detail) ? detail?.code : undefined;
  const kind: SearchErrorKind = res.status === 422 ? "invalid" : (code && KIND_BY_CODE[code]) || "server";
  const message = kind !== "invalid" && typeof detail?.message === "string" ? detail.message : DEFAULT_MESSAGES[kind];
  throw new SearchApiError(kind, message);
}

export function searchGdpr(question: string, signal: AbortSignal): Promise<SearchResult> {
  return request("/api/search", SearchResultSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
}

export async function getEngineState(signal: AbortSignal): Promise<EngineState> {
  return (await request("/api/search/status", EngineStatusSchema, { signal })).state;
}
