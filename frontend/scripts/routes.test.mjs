// Route smoke tests against a running frontend (dev or production server). No dependencies: Node's built-in runner.
//   npm run dev            # or: npm run build && npm run start -- -p 4001
//   npm run test:routes    # BASE_URL=http://localhost:4001 by default
import assert from "node:assert/strict";
import { test } from "node:test";

const BASE = process.env.BASE_URL ?? "http://localhost:4001";
const PRODUCT = "Regulatory & Compliance Intelligence Hub";
const ROUTES = ["/", "/about", "/faq", "/help", "/contact", "/terms", "/privacy", "/cookies", "/disclaimer"];

const get = (path) => fetch(new URL(path, BASE), { redirect: "manual" });
const text = async (path) => (await get(path)).text();
// React inserts <!-- --> markers between adjacent text segments when rendering on the server; they are invisible.
const decode = (s) => s.replaceAll("<!-- -->", "").replaceAll("&amp;", "&").replaceAll("&#x27;", "'");

test("every page responds 200 with exactly one h1 and a titled document", async () => {
  for (const route of ROUTES) {
    const res = await get(route);
    assert.equal(res.status, 200, `${route} -> ${res.status}`);
    const html = await res.text();
    assert.equal((html.match(/<h1[\s>]/g) ?? []).length, 1, `${route} must have exactly one <h1>`);
    const title = decode(html.match(/<title>([^<]*)<\/title>/)?.[1] ?? "");
    assert.ok(title.includes(PRODUCT), `${route} title "${title}" should name the product`);
  }
});

test("the footer groups its links and every link opens a real page", async () => {
  const html = await text("/");
  const nav = html.match(/<nav aria-label="Footer".*?<\/nav>/s)?.[0];
  assert.ok(nav, "footer navigation is present");
  for (const group of ["Product", "Legal", "Support"]) assert.ok(nav.includes(`>${group}<`), `group ${group}`);
  const hrefs = [...nav.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(hrefs.length >= 9, `expected at least 9 footer links, found ${hrefs.length}`);
  for (const href of hrefs) {
    assert.ok(href.startsWith("/"), `${href} should be an internal page`);
    const res = await get(href.split("#")[0]);
    assert.equal(res.status, 200, `${href} -> ${res.status}`);
  }
});

test("section anchors that the footer and other pages link to exist", async () => {
  const about = await text("/about");
  assert.ok(about.includes('id="how-it-works"'), "/about#how-it-works");
  const faq = await text("/faq");
  for (const id of ["no-answer", "engine-unavailable", "query-data"]) assert.ok(faq.includes(`id="${id}"`), `/faq#${id}`);
  assert.ok((await text("/help")).includes('id="when-something-goes-wrong"'), "/help#when-something-goes-wrong");
});

test("the copyright line names the product and the current year", async () => {
  const html = decode(await text("/"));
  assert.ok(html.includes(`© ${new Date().getFullYear()} ${PRODUCT}`), "copyright notice");
});

test("no page tells end users to read developer documentation", async () => {
  for (const route of ROUTES) {
    const html = decode(await text(route)).replace(/<script.*?<\/script>/gs, "").replace(/<[^>]+>/g, " ");
    assert.ok(!/README/.test(html), `${route} mentions the README`);
  }
});

test("the FAQ covers the questions users actually ask", async () => {
  const faq = decode(await text("/faq"));
  for (const q of [
    "What is the Regulatory",
    "How does the search work",
    "Where do the answers and citations come from",
    "How can I verify a cited article",
    "can’t find a relevant answer",
    "Why might a search fail",
    "search engine is unavailable",
    "Is the information legal advice",
    "query data handled",
    "report a problem",
  ]) assert.ok(faq.includes(q), `FAQ should include: ${q}`);
});

test("removed and unknown routes return 404", async () => {
  for (const route of ["/search", "/no-such-page", "/api/health-ui"]) assert.equal((await get(route)).status, 404, route);
});
