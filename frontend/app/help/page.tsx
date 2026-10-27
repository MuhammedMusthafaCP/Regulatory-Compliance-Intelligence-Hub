import type { Metadata } from "next";
import { ContentPage, ExtLink, Fact, Facts, PageLink, Section, Ul } from "../_components/ContentPage";
import { site } from "../_content/site";

export const metadata: Metadata = {
  title: "Help",
  description: "How to get good results, how to read them, and what to do when something goes wrong.",
};

export default function HelpPage() {
  return (
    <ContentPage title="Help" intro="How to get good results, how to read them, and what to do when something goes wrong.">
      <Section title="Getting good results">
        <Ul>
          <li>Ask one question at a time, in plain language, in up to 500 characters.</li>
          <li>
            Be specific about the situation. “How long may a company keep my data after I withdraw consent?” works
            better than “data retention”.
          </li>
          <li>
            The Regulation’s own terms help: <em>controller</em>, <em>processor</em>, <em>data subject</em>,{" "}
            <em>supervisory authority</em>, <em>personal data breach</em>, <em>consent</em>.
          </li>
          <li>Every question is searched on its own; the service does not remember your earlier ones.</li>
          <li>If a result looks wrong, rephrase and try again, and always check the cited text.</li>
        </Ul>
      </Section>

      <Section title="Reading a result">
        <Facts>
          <Fact term="The label">
            <p>
              <em>Supported by the Regulation</em>, <em>Weak match</em> or <em>No basis in the GDPR</em>. It reflects a
              relevance score, not a legal judgement.
            </p>
          </Fact>
          <Fact term="Provisions">
            <p>
              The operative text of the articles, best match first, each with its citation (such as Article 6(1)(f)).
              Choose “Show full text” to expand a long provision.
            </p>
          </Fact>
          <Fact term="Recitals">
            <p>Context that explains the purpose of the rules. Helpful for interpretation, but not binding.</p>
          </Fact>
          <Fact term="Read on EUR-Lex">
            <p>Opens that passage in the official text in a new tab, so you can verify it.</p>
          </Fact>
          <Fact term="Match score">
            <p>
              A number from 0 to 1 for how well the best provision matches your question. It is a relative signal, not a
              probability, and close matches often score similarly.
            </p>
          </Fact>
        </Facts>
      </Section>

      <Section id="when-something-goes-wrong" title="When something goes wrong">
        <Facts>
          <Fact term="Search is starting up">
            <p>The service is loading. Wait a few seconds; the Search button enables itself when it is ready.</p>
          </Fact>
          <Fact term="Search is temporarily unavailable">
            <p>
              The service is set up but could not start, which is usually temporary. Choose “Try again” after a short
              wait. If it keeps happening, <PageLink href="/contact">contact support</PageLink>.
            </p>
          </Fact>
          <Fact term="Search is currently unavailable">
            <p>
              The search service has not been configured on this server. Only its administrator can fix that, so please{" "}
              <PageLink href="/contact">get in touch</PageLink>.
            </p>
          </Fact>
          <Fact term="The search engine is busy">
            <p>Too many searches are waiting. Try again in a few seconds.</p>
          </Fact>
          <Fact term="The search took too long">
            <p>Try again, or shorten the question.</p>
          </Fact>
          <Fact term="We can’t reach the search service">
            <p>
              Your connection or the service may be down. Check your connection and try again; if the problem
              continues, the service may be undergoing maintenance.
            </p>
          </Fact>
          <Fact term="No basis in the GDPR">
            <p>
              The question isn’t about the GDPR, or the Regulation doesn’t settle it. See the{" "}
              <PageLink href="/faq#no-answer">FAQ</PageLink>.
            </p>
          </Fact>
        </Facts>
      </Section>

      <Section title="Checking a citation">
        <p>
          Every provision links to its place in the official text on <ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink>.
          The Official Journal of the European Union is the authoritative source; this service quotes the original text
          of 4 May 2016, which may not include later corrections.
        </p>
      </Section>

      <Section title="If you run this service">
        <p>
          Setup, configuration and troubleshooting for administrators are in the{" "}
          <ExtLink href={`${site.repoUrl}#readme`}>project documentation</ExtLink>.
        </p>
      </Section>

      <Section title="Still need help?">
        <p>
          Browse the <PageLink href="/faq">FAQ</PageLink> or <PageLink href="/contact">contact support</PageLink>.
        </p>
      </Section>
    </ContentPage>
  );
}
