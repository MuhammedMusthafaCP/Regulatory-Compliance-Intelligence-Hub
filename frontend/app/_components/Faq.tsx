import type { ReactNode } from "react";

export interface FaqItem {
  id: string;
  question: string;
  answer: ReactNode;
}

/** Native <details> accordion: keyboard and screen-reader accessible without any script. */
export function Faq({ items }: { items: FaqItem[] }) {
  return (
    <div className="border-y border-rule">
      {items.map((item) => (
        <details key={item.id} className="group border-t border-rule first:border-t-0">
          <summary className="flex cursor-pointer list-none items-start justify-between gap-4 rounded-sm py-5 font-display text-heading font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand [&::-webkit-details-marker]:hidden">
            <span>{item.question}</span>
            <span
              aria-hidden
              className="mt-0.5 shrink-0 font-ui text-title font-normal leading-none text-brand transition-transform group-open:rotate-45 motion-reduce:transition-none"
            >
              +
            </span>
          </summary>
          <div id={item.id} className="max-w-[68ch] space-y-3 pb-6 text-body text-ink-soft">
            {item.answer}
          </div>
        </details>
      ))}
    </div>
  );
}
