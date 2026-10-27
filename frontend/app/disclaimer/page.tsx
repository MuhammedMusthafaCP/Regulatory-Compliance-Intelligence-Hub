import type { Metadata } from "next";
import { Callout, ContentPage, ExtLink, PageLink, Section, Ul } from "../_components/ContentPage";
import { site } from "../_content/site";

export const metadata: Metadata = {
  title: "Disclaimer",
  description: "The limits of the service, and the official sources it quotes.",
};

export default function DisclaimerPage() {
  return (
    <ContentPage
      title="Disclaimer"
      intro="What the service is for, what it is not, and where the official text lives."
      updated={site.documentsUpdated}
    >
      <Callout title="Please read">
        <p>
          The service helps you find and read regulatory text. It is not legal advice and it does not replace a
          qualified professional.
        </p>
      </Callout>

      <Section title="Purpose of the service">
        <p>
          Search results are intended to help you locate and understand the text of {site.regulation} (the GDPR). Each
          result is a quotation from the Regulation with its citation. The service does not interpret the law for you or
          apply it to your situation.
        </p>
      </Section>

      <Section title="Not legal advice">
        <p>
          Nothing on this service is legal, compliance or other professional advice. Using it does not create a
          professional relationship. For any decision with legal consequences, consult a qualified lawyer or your data
          protection officer.
        </p>
      </Section>

      <Section title="Grounded in sources, but not infallible">
        <Ul>
          <li>Results are drawn from the Regulation’s text. The service does not invent provisions or citations.</li>
          <li>
            Finding the right provision is a matter of ranking and judgement by software. It can miss a relevant
            provision, rank a less relevant one first, or call a match strong or weak when a person would disagree.
          </li>
          <li>
            Its copy is the original text published in the Official Journal on 4 May 2016. It may not include later
            corrections, and it covers the GDPR only.
          </li>
          <li>The accuracy and completeness of any result depend on that source material and on the software’s behaviour.</li>
          <li>
            Recitals are explanatory and not binding; the provisions of the articles are the operative text.
          </li>
        </Ul>
      </Section>

      <Section title="Verify before you rely on it">
        <p>
          Check every consequential point against the authoritative text. Each result links to its passage on{" "}
          <ExtLink href={site.sourceUrl}>EUR-Lex</ExtLink>, and the Official Journal of the European Union is the
          authoritative source. Read the surrounding provisions too: one paragraph seldom tells the whole story.
        </p>
      </Section>

      <Section title="Source and attribution">
        <p>
          The text of {site.regulation} is © European Union. EUR-Lex legal documents may be reused for commercial and
          non-commercial purposes under Commission Decision 2011/833/EU, with the source acknowledged. The service
          is not affiliated with, or endorsed by, the European Union or its institutions.
        </p>
      </Section>

      <Section title="Limitation">
        <p>
          The service is provided as available, without warranty, and is not responsible for decisions made on the basis
          of its results, to the extent the law allows. See the <PageLink href="/terms">Terms and Conditions</PageLink>{" "}
          for the full terms.
        </p>
      </Section>
    </ContentPage>
  );
}
