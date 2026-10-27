import type { Metadata } from "next";
import { Callout, ContentPage, ExtLink, PageLink, Section, Ul } from "../_components/ContentPage";
import { operatorName, site } from "../_content/site";

export const metadata: Metadata = {
  title: "Contact",
  description: "How to report a problem or ask for help with the Hub.",
};

export default function ContactPage() {
  return (
    <ContentPage title="Contact and support" intro="How to report a problem or ask for help.">
      <Section title="Ask for help">
        {site.supportEmail ? (
          <p>
            Email{" "}
            <a
              href={`mailto:${site.supportEmail}`}
              className="rounded-sm font-medium text-brand underline decoration-lake decoration-2 underline-offset-4 hover:text-brand-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              {site.supportEmail}
            </a>
            . There is no guaranteed response time.
          </p>
        ) : (
          <p>
            This service has not published a support email address. If you were given access by an organisation, contact
            its administrator. If search shows that it is unavailable, the administrator is the person who can restore
            it.
          </p>
        )}
        <p>
          The service is run by {operatorName}. How your data is handled is explained in the{" "}
          <PageLink href="/privacy">Privacy Policy</PageLink>.
        </p>
      </Section>

      <Section title="Report a problem or suggest an improvement">
        <p>
          You can open an issue on the project’s <ExtLink href={site.issuesUrl}>public issue tracker</ExtLink>. Issues are
          visible to everyone, so please don’t include personal data or confidential information.
        </p>
        <p>Helpful details to include:</p>
        <Ul>
          <li>What you did and what you expected.</li>
          <li>The message the page showed.</li>
          <li>Roughly when it happened and which device and browser you used.</li>
          <li>The question you asked, if it isn’t sensitive.</li>
        </Ul>
      </Section>

      <Section title="What support can’t do">
        <Callout>
          <p>
            Support can help with using the service and with problems with it. It cannot give legal advice or tell you
            how the Regulation applies to your circumstances; for that, consult a qualified professional.
          </p>
        </Callout>
      </Section>
    </ContentPage>
  );
}
