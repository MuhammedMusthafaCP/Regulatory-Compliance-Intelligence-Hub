import type { Metadata } from "next";
import { Callout, ContentPage, ExtLink, Fact, Facts, LegalStatus, PageLink, Section, Ul } from "../_components/ContentPage";
import { operatorName, site } from "../_content/site";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "What the Hub does and does not do with your questions and with technical data.",
};

export default function PrivacyPage() {
  return (
    <ContentPage
      title="Privacy Policy"
      intro="This policy describes what the service does with your data, based on how the software actually works."
      updated={site.documentsUpdated}
    >
      <Callout title="In short">
        <p>
          Your question is used to run your search and is not stored by the application, written to its logs, or sent
          to any third-party AI or search service. There are no accounts, no cookies, no analytics and no advertising.
        </p>
      </Callout>

      <Section title="Who is responsible">
        <p>
          The service is run by {operatorName}, which is the party responsible for the processing described here. See{" "}
          <PageLink href="/contact">Contact</PageLink> for how to reach them.
        </p>
      </Section>

      <Section title="What is processed">
        <Facts>
          <Fact term="Your question">
            <p>
              The text you type is sent to the service’s server and held in memory only while your search runs. It is
              compared with the Regulation’s text by models that run on the service’s own servers. It is not saved to
              a database or file, and the application does not write it to its logs.
            </p>
          </Fact>
          <Fact term="Technical request data">
            <p>
              Like any web service, the server handles your network address and the time, the page or endpoint
              requested and the response status. The application server writes standard request log lines containing
              these details (not your question). Hosting, proxy or network providers used by the operator may also keep
              their own logs.
            </p>
          </Fact>
          <Fact term="Error diagnostics">
            <p>
              If a search fails unexpectedly, a technical error record may be logged to help fix the fault. The
              application does not intentionally record question text in it.
            </p>
          </Fact>
          <Fact term="Not collected">
            <p>
              No account or sign-in, no name or email address, no analytics or advertising identifiers, and no
              profiling.
            </p>
          </Fact>
        </Facts>
      </Section>

      <Section title="Where processing happens, and third parties">
        <Ul>
          <li>
            Searches are run by software on the operator’s servers. Your question is not passed to a third-party AI,
            search or analytics provider.
          </li>
          <li>
            The Regulation’s text is stored in a hosted PostgreSQL database (the reference setup uses Neon). It holds
            the regulation text only, and your questions are not sent to it.
          </li>
          <li>
            Fonts and other page assets are served by the service itself; the page loads nothing from third-party
            hosts.
          </li>
          <li>
            Links to <ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink> take you to a site run by the Publications Office
            of the European Union, which has its own policies.
          </li>
        </Ul>
        <p>Deployments can differ; the operator should say so here if theirs does.</p>
      </Section>

      <Section title="How long data is kept">
        <p>
          Questions are not retained: they exist in memory while the search runs. Server and provider logs are kept for
          as long as the operator’s logging and hosting configuration keeps them; the application does not set a
          retention period itself, so the operator should state theirs.
        </p>
      </Section>

      <Section title="Cookies and browser storage">
        <p>
          The service does not use cookies or browser storage. See the <PageLink href="/cookies">Cookie Policy</PageLink>.
        </p>
      </Section>

      <Section title="Your rights">
        <p>
          Depending on where you live, data protection law, including the GDPR, may give you rights to access, correct
          or delete personal data held about you, to restrict or object to its processing, to data portability, and to
          complain to a supervisory authority. Because the application keeps no record of your questions and has no
          accounts, there is little for it to disclose or delete; requests about log data should go to the operator
          through <PageLink href="/contact">Contact</PageLink>.
        </p>
        <p>
          Which legal basis applies to the operator’s logging, and any international transfers by their hosting
          providers, depend on the operator’s own circumstances.
        </p>
      </Section>

      <Section title="Children">
        <p>The service is a professional research tool and is not directed at children.</p>
      </Section>

      <Section title="Changes">
        <p>This policy will be updated if the software’s data practices change; the date above shows the latest version.</p>
      </Section>

      <LegalStatus />
    </ContentPage>
  );
}
