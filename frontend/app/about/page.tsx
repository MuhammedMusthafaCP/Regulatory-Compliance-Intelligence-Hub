import type { Metadata } from "next";
import { Callout, ContentPage, ExtLink, Ol, PageLink, Section, Ul } from "../_components/ContentPage";
import { site } from "../_content/site";

export const metadata: Metadata = {
  title: "About",
  description: "What the Regulatory & Compliance Intelligence Hub does, who it is for, and how it works.",
};

export default function AboutPage() {
  return (
    <ContentPage
      title="About the Hub"
      intro={`The ${site.name} helps you find the provisions of ${site.regulation}, the GDPR, that answer a question, with every result tied to the article it comes from.`}
    >
      <Section title="What it is">
        <p>
          The Hub is a search service built on one principle: answers about regulation should come from the official
          text and be easy to check. It finds the provisions that bear on your question and quotes them exactly, with a
          citation and a link to the source. It does not write answers of its own.
        </p>
        <p>
          When the Regulation does not support an answer, it says so instead of showing provisions that merely look
          related.
        </p>
      </Section>

      <Section title="What you can do today">
        <Ul>
          <li>Ask a question in plain language, such as “How quickly must a data breach be reported?”.</li>
          <li>Read the matching provisions (article, paragraph and point) in the Regulation’s exact words.</li>
          <li>See related recitals separately, as context that explains the purpose of the rules.</li>
          <li>Open any result on EUR-Lex to check it against the official text.</li>
          <li>Get a clear signal when a match is strong, weak, or absent.</li>
        </Ul>
      </Section>

      <Section title="Who it is for">
        <p>
          People who need to locate and read GDPR text quickly: compliance and privacy teams, data protection officers,
          and the legal, product and engineering colleagues who work with them. It is a finding aid, not an adviser;
          see the <PageLink href="/disclaimer">Disclaimer</PageLink>.
        </p>
      </Section>

      <Section id="how-it-works" title="How it works">
        <Ol>
          <li>
            <strong className="text-ink">You ask.</strong> Your question is sent to the service and handled on its own
            servers.
          </li>
          <li>
            <strong className="text-ink">Finding candidates.</strong> The question is compared, by meaning and by
            keywords, with every provision of the Regulation’s articles. Everyday phrasing is mapped to the
            Regulation’s own wording, so “companies outside the EU” can reach “not established in the Union”.
          </li>
          <li>
            <strong className="text-ink">Re-reading.</strong> A second model scores each candidate against your exact
            question and puts the best first.
          </li>
          <li>
            <strong className="text-ink">An honest signal.</strong> The best score decides the label: supported, weak
            match, or no basis in the GDPR.
          </li>
          <li>
            <strong className="text-ink">Showing the text.</strong> Articles, the operative law, are shown first.
            Recitals appear separately as interpretive context, never as the answer.
          </li>
        </Ol>
        <p>The models run on the service’s own infrastructure. Your question is not sent to a third-party AI service.</p>
      </Section>

      <Section title="What it does not do">
        <Ul>
          <li>It covers only the GDPR. Other regulations are not included.</li>
          <li>
            Its copy is the original text published in the Official Journal on 4 May 2016, so it may not include later
            corrections.
          </li>
          <li>It treats every question on its own and does not remember earlier ones.</li>
          <li>It does not read your documents or policies, and it does not generate explanations.</li>
          <li>It does not give legal advice.</li>
        </Ul>
      </Section>

      <Section title="Source and attribution">
        <p>
          The text comes from the English edition of {site.regulation} on <ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink>,
          © European Union, reused under Commission Decision 2011/833/EU. The Official Journal of the European Union is
          the authoritative source.
        </p>
        <Callout>
          <p>
            Questions about these terms of use or how your data is handled? See the{" "}
            <PageLink href="/terms">Terms</PageLink> and the <PageLink href="/privacy">Privacy Policy</PageLink>.
          </p>
        </Callout>
      </Section>
    </ContentPage>
  );
}
