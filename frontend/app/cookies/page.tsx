import type { Metadata } from "next";
import { Callout, ContentPage, Fact, Facts, LegalStatus, PageLink, Section } from "../_components/ContentPage";
import { site } from "../_content/site";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: "The Hub does not use cookies, browser storage or tracking technologies.",
};

export default function CookiePolicyPage() {
  return (
    <ContentPage
      title="Cookie Policy"
      intro="This page explains which cookies and similar technologies the service uses. Today, that is none."
      updated={site.documentsUpdated}
    >
      <Callout title="In short">
        <p>
          The service sets no cookies, stores nothing in your browser, and runs no analytics, advertising or tracking.
          For that reason it shows no cookie banner and asks for no consent.
        </p>
      </Callout>

      <Section title="What we checked">
        <Facts>
          <Fact term="Cookies">
            <p>None. The service neither sets nor reads cookies.</p>
          </Fact>
          <Fact term="Local, session and database storage">
            <p>None. Nothing is saved in your browser between visits, and your questions are not kept on your device.</p>
          </Fact>
          <Fact term="Analytics and advertising">
            <p>None. There are no analytics scripts, advertising identifiers, tracking pixels or fingerprinting.</p>
          </Fact>
          <Fact term="Third-party content">
            <p>
              None is loaded automatically. Fonts and scripts come from the service itself. If you follow a link to
              EUR-Lex, that site applies its own policies.
            </p>
          </Fact>
        </Facts>
      </Section>

      <Section title="Why there is no consent banner">
        <p>
          Consent rules for cookies and similar technologies apply to technologies that store or read information on
          your device. Since the service uses none, there is nothing to consent to, and a banner would only be noise.
        </p>
      </Section>

      <Section title="Checking for yourself">
        <p>
          In your browser’s developer tools, the Application (or Storage) panel shows cookies and stored data for the
          site, and the Network panel shows every request it makes.
        </p>
      </Section>

      <Section title="If this changes">
        <p>
          If the service ever adds cookies, storage or analytics, this policy and the{" "}
          <PageLink href="/privacy">Privacy Policy</PageLink> will be updated first, and a consent mechanism will be
          added wherever the rules require one.
        </p>
      </Section>

      <LegalStatus />
    </ContentPage>
  );
}
