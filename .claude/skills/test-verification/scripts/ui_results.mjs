// Browser test of the Results module on TEST. Logins come only from env vars
// (KIS_U1 super-admin, KIS_U2 admin, KIS_PW); nothing is written to disk but screenshots.
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.PW_DEPS + "/package.json");
const { chromium } = require("playwright-core");
const BASE = "http://69.62.72.137/kisschool/admin";
const SHOTS = process.env.SHOTS;
const out = { steps: [], issues: [] };
const browser = await chromium.launch({ channel: "chrome", headless: true });

function watch(page, tag) {
  page.on("console", (m) => { if (m.type() === "error") out.issues.push({ tag, kind: "console", text: m.text().slice(0, 220) }); });
  page.on("pageerror", (e) => out.issues.push({ tag, kind: "pageerror", text: String(e).slice(0, 220) }));
  page.on("response", (r) => {
    const u = r.url();
    if (r.status() >= 400 && u.includes("/kisschool/")) out.issues.push({ tag, kind: "http", text: `${r.status()} ${r.request().method()} ${u.replace(/^.*\/kisschool/, "")}`.slice(0, 220) });
  });
}
async function step(name, fn) {
  const t0 = Date.now();
  try { const info = await fn(); out.steps.push({ name, ok: true, ms: Date.now() - t0, info }); }
  catch (e) { out.steps.push({ name, ok: false, ms: Date.now() - t0, error: String(e.message || e).split("\n")[0].slice(0, 240) }); }
}
const shot = (page, f, full = true) => page.screenshot({ path: `${SHOTS}/${f}`, fullPage: full });
async function login(page, user) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.fill('input[autocomplete="username"]', user);
  await page.fill('input[autocomplete="current-password"]', process.env.KIS_PW);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 20000 });
  await page.waitForTimeout(800);
  return page.url().replace(BASE, "");
}
async function pick(page, triggerSel, optionName) {
  await page.locator(triggerSel).first().click();
  if (optionName === null) await page.getByRole("option").first().click();
  else await page.getByRole("option", { name: optionName, exact: true }).click();
  await page.waitForTimeout(1200);
}
const go = async (page, path) => { await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" }); await page.waitForTimeout(1500); return page.url().replace(BASE, ""); };
const bodyText = async (page, n = 300) => (await page.locator("main").first().innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, n);

// ── super-admin, desktop ──
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const page = await ctx.newPage(); watch(page, "super");
await step("login super-admin", () => login(page, process.env.KIS_U1));
await step("results: 8th opens on term 1 (fallback)", async () => {
  await go(page, "/marks/results");
  await pick(page, '[id$="-class"]', "8th");
  const note = await page.getByText(/No Term 2 marks yet/).count();
  const scopeShown = (await page.locator('[id$="-scope"]').first().innerText()).trim();
  if (!note || scopeShown !== "Term 1") throw new Error(`note=${note} scope=${scopeShown}`);
  await page.locator("table").first().waitFor({ timeout: 15000 });
  const heads = await page.locator("table").first().locator("thead th").allInnerTexts();
  const rows = await page.locator("table").first().locator("tbody tr").count();
  await shot(page, "results-term1.png");
  return { rows, heads: heads.map((h) => h.replace(/\s+/g, " ")).join(" | ").slice(0, 300) };
});
await step("results: show each exam", async () => {
  await page.getByText("Show each exam", { exact: true }).click();
  await page.waitForTimeout(600);
  await shot(page, "results-each-exam.png");
  return { heads: (await page.locator("table").first().locator("thead th").count()) };
});
await step("results: export CSV", async () => {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 10000 }), page.getByRole("button", { name: /Export CSV/ }).click()]);
  const p = `${SHOTS}/results.csv`; await dl.saveAs(p);
  const lines = fs.readFileSync(p, "utf8").split(/\r?\n/);
  return { file: dl.suggestedFilename(), lines: lines.length, head: lines.slice(0, 3).join(" ⏎ ").slice(0, 300) };
});
await step("results: print view", async () => {
  await page.emulateMedia({ media: "print" });
  const navVisible = await page.locator("header, nav, aside").evaluateAll((els) => els.filter((e) => e.offsetParent !== null && getComputedStyle(e).display !== "none").length);
  await shot(page, "results-print.png");
  await page.emulateMedia({ media: "screen" });
  return { visibleChromeInPrint: navVisible };
});
for (const scope of ["Term 2", "Annual"]) {
  await step(`results: ${scope}`, async () => {
    await pick(page, '[id$="-scope"]', scope);
    await page.waitForTimeout(500);
    await shot(page, `results-${scope.replace(" ", "").toLowerCase()}.png`);
    return { rows: await page.locator("table").first().locator("tbody tr").count().catch(() => -1), text: await bodyText(page, 160) };
  });
}
await step("report cards tab", async () => {
  await pick(page, '[id$="-scope"]', "Term 1");
  await page.getByRole("tab", { name: "Report cards" }).click();
  await page.waitForTimeout(1500);
  await shot(page, "report-cards-tab.png");
  return { text: await bodyText(page, 400) };
});
await step("templates list + detail", async () => {
  await go(page, "/templates");
  await shot(page, "templates.png");
  const links = page.locator('a[href*="/templates/"]');
  const n = await links.count();
  if (n) { await links.first().click(); await page.waitForTimeout(1800); await shot(page, "template-detail.png"); }
  return { templates: n, at: page.url().replace(BASE, ""), text: await bodyText(page, 200) };
});
await step("marks entry", async () => {
  await go(page, "/marks/entry");
  const ids = await page.locator('[id]').evaluateAll((els) => els.map((e) => e.id).filter((i) => /-(class|subject|exam|test|session)$/.test(i)));
  const picked = [];
  for (const [sel, opt] of [['[id$="-class"]', "8th"], ['[id$="-subject"]', null], ['[id$="-exam"]', null], ['[id$="-test"]', null]]) {
    try { if (await page.locator(sel).count()) { await pick(page, sel, opt); picked.push(sel); } } catch (e) { picked.push(sel + " FAILED"); }
  }
  const studentRows = await page.locator("table tbody tr, [data-student-row]").count();
  await shot(page, "marks-entry.png");
  return { pickers: ids.join(","), picked: picked.join(","), studentRows, text: await bodyText(page, 260) };
});
await step("sessions + defaults prefill", async () => {
  await go(page, "/sessions");
  await shot(page, "sessions.png");
  const btn = page.getByRole("button", { name: /New session|Add session/i });
  if (!(await btn.count())) return { note: "no create button", text: await bodyText(page, 200) };
  await btn.first().click();
  const dlg = page.getByRole("dialog");
  await dlg.locator("input").first().fill("2027-28");
  await page.waitForTimeout(2000);
  await shot(page, "sessions-dialog.png", false);
  const txt = (await dlg.innerText()).replace(/\s+/g, " ").slice(0, 300);
  await page.keyboard.press("Escape");
  return { dialog: txt };
});
await step("punjabi toggle on results", async () => {
  await go(page, "/marks/results");
  await pick(page, '[id$="-class"]', "8th");
  const pa = page.locator("button[aria-pressed]").filter({ hasText: /ਪੰ/ });
  await pa.first().click(); await page.waitForTimeout(800);
  await shot(page, "results-pa.png");
  const t = await bodyText(page, 220);
  await page.locator("button[aria-pressed]").filter({ hasText: /EN/i }).first().click();
  return { text: t };
});
await ctx.close();

// ── super-admin, phone width ──
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
const m = await mctx.newPage(); watch(m, "mobile");
await step("mobile: results 8th", async () => {
  await login(m, process.env.KIS_U1);
  await go(m, "/marks/results");
  await pick(m, '[id$="-class"]', "8th");
  await m.waitForTimeout(800);
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await shot(m, "mobile-results.png", false);
  return { pageOverflowPx: overflow };
});
await mctx.close();

// ── admin ──
const actx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const a = await actx.newPage(); watch(a, "admin");
await step("login admin", () => login(a, process.env.KIS_U2));
await step("admin: results + report cards", async () => {
  await go(a, "/marks/results"); await pick(a, '[id$="-class"]', "8th");
  await a.getByRole("tab", { name: "Report cards" }).click(); await a.waitForTimeout(1000);
  await shot(a, "admin-report-cards.png");
  return { text: await bodyText(a, 200) };
});
await step("admin: super-admin pages blocked", async () => ({ sessions: await go(a, "/sessions"), classSubjects: await go(a, "/class-subjects") }));
await actx.close();
await browser.close();
console.log(JSON.stringify(out, null, 1));
