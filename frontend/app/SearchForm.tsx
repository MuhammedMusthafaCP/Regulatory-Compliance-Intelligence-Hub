"use client";

import { useId } from "react";
import { MAX_QUESTION_LENGTH } from "./api";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
  disabled: boolean;
  disabledLabel?: string;
  error?: string | null;
}

export default function SearchForm({ value, onChange, onSubmit, busy, disabled, disabledLabel, error }: Props) {
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const nearLimit = value.length > MAX_QUESTION_LENGTH * 0.8;

  return (
    <form
      role="search"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor={inputId} className="text-meta font-semibold uppercase text-ink-muted">
        Your question
      </label>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row">
        <input
          id={inputId}
          type="search"
          enterKeyHint="search"
          autoComplete="off"
          maxLength={MAX_QUESTION_LENGTH}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && onChange("")}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          placeholder="e.g. When must a data breach be reported?"
          className="h-14 min-w-0 flex-1 rounded-md border border-ink/30 bg-paper-raised px-4 text-body text-ink placeholder:text-ink-muted/80 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand aria-[invalid=true]:border-signal-error"
        />
        <button
          type="submit"
          disabled={busy || disabled}
          className="h-14 shrink-0 rounded-md bg-brand px-8 text-ui font-semibold text-white transition-colors hover:bg-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:cursor-not-allowed disabled:bg-ink-muted/60"
        >
          {busy ? "Searching…" : disabledLabel ?? "Search"}
        </button>
      </div>
      <div className="mt-2 flex min-h-[1.25rem] justify-between gap-4 text-ui">
        <p id={errorId} role={error ? "alert" : undefined} className="text-signal-error">
          {error}
        </p>
        {nearLimit && (
          <p className="ml-auto tabular-nums text-ink-muted">
            {value.length}/{MAX_QUESTION_LENGTH}
          </p>
        )}
      </div>
    </form>
  );
}
