import type { Metadata } from "next";
import { ContentPage, ExtLink, LegalStatus, PageLink, Section, Ul } from "../_components/ContentPage";
import { operatorName, site } from "../_content/site";

export const metadata: Metadata = {
  title: "Terms and Conditions",
  description: "The terms that govern use of the Regulatory & Compliance Intelligence Hub.",
};

export default function TermsPage() {
  return (
    <ContentPage
      title="Terms and Conditions"
      intro={`These terms govern your use of the ${site.name} (the “service”), which is run by ${operatorName}. By using the service you agree to them.`}
      updated={site.documentsUpdated}
    >
      <Section title="1. What the service is">
        <p>
          The service helps you find and read the provisions of {site.regulation} (the GDPR). It retrieves and quotes
          the official text and indicates how closely each provision matches your question. It is an information tool.
        </p>
      </Section>

      <Section title="2. Not legal advice">
        <p>
          Nothing the service shows is legal advice, and no lawyer–client relationship arises from using it. Results
          can be incomplete or ranked imperfectly, and the service does not know your facts, your jurisdiction or your
          circumstances. Read the authoritative text and take qualified advice before acting on anything you find. The{" "}
          <PageLink href="/disclaimer">Disclaimer</PageLink> forms part of these terms.
        </p>
      </Section>

      <Section title="3. Permitted use">
        <p>
          You may use the service to look up and read regulatory text for your own work or your organisation’s internal
          purposes, and to quote or link to the passages it shows, with the source acknowledged.
        </p>
      </Section>

      <Section title="4. What you must not do">
        <Ul>
          <li>Use the service unlawfully, or to harm, deceive or harass anyone.</li>
          <li>
            Try to disrupt or overload it, probe it for weaknesses, or bypass its limits. Searches are processed one at
            a time and may be rejected when it is busy.
          </li>
          <li>Send large volumes of automated requests without the operator’s agreement.</li>
          <li>Present its results as official publications, as legal advice, or as an endorsement by any authority.</li>
        </Ul>
      </Section>

      <Section title="5. Your responsibilities">
        <Ul>
          <li>Verify what matters against the Official Journal text, using the links the service provides.</li>
          <li>Keep personal data and confidential information out of your questions.</li>
          <li>Make your own decisions and take responsibility for how you use what you find.</li>
        </Ul>
      </Section>

      <Section title="6. Availability and changes to the service">
        <p>
          The service is provided as available. It can be slow, limited, interrupted or withdrawn, and its content,
          behaviour and the Regulation’s text it holds can change without notice. The copy of the Regulation it holds
          is the original text published on 4 May 2016 and may not reflect later corrections.
        </p>
      </Section>

      <Section title="7. Intellectual property">
        <p>
          The text of the Regulation is © European Union and is reused under Commission Decision 2011/833/EU, with the
          source acknowledged (<ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink>). Rights in the software, the interface
          and the original content of the service belong to {operatorName} or its licensors. Except as these terms
          allow, no licence to them is granted.
        </p>
      </Section>

      <Section title="8. Warranties and liability">
        <p>
          To the extent the law allows, the service and its content are provided “as is”, without warranties of
          accuracy, completeness, fitness for a purpose or uninterrupted operation, and {operatorName} is not liable for
          loss arising from your use of, or inability to use, the service or from reliance on its results. Nothing in
          these terms excludes or limits liability that cannot lawfully be excluded or limited.
        </p>
      </Section>

      <Section title="9. Suspension and termination">
        <p>
          {operatorName} may suspend or end your access at any time, for example if you breach these terms or to protect
          the service. You can stop using it at any time.
        </p>
      </Section>

      <Section title="10. Changes to these terms">
        <p>
          These terms may be updated; the date above shows the latest version. Continuing to use the service after a
          change means you accept the updated terms.
        </p>
      </Section>

      <Section title="11. Contact">
        <p>
          Questions about these terms: see <PageLink href="/contact">Contact</PageLink>. How your data is handled is
          explained in the <PageLink href="/privacy">Privacy Policy</PageLink> and the{" "}
          <PageLink href="/cookies">Cookie Policy</PageLink>.
        </p>
      </Section>

      <LegalStatus />
      <p className="max-w-[68ch] text-ui text-ink-muted">
        These terms do not choose a governing law or a court, and they do not address consumer-protection rules that
        differ between countries. Those provisions depend on who operates the service and where, and need legal input
        from the operator.
      </p>
    </ContentPage>
  );
}
