// Teacher-view browser test on TEST (no saves). Logins only from env vars; the
// teacher is found through the API and never printed (no name, email or phone).
import { createRequire } from "node:module";
const require = createRequire(process.env.PW_DEPS + "/package.json");
const { chromium, request } = require("playwright-core");
const ORIGIN = "http://69.62.72.137";
const BASE = `${ORIGIN}/kisschool/admin`;
const SHOTS = process.env.SHOTS;
const out = { steps: [], issues: [] };
const step = async (name, fn) => {
  try { out.steps.push({ name, ok: true, info: await fn() }); }
  catch (e) { out.steps.push({ name, ok: false, error: String(e.message || e).split("\n")[0].slice(0, 240) }); }
};

const api = await request.newContext({ baseURL: `${ORIGIN}/kisschool/api/` });
let r = await api.post("auth/login", { data: { identifier: process.env.KIS_U1, password: process.env.KIS_PW } });
const superTok = (await r.json()).token;
r = await api.get("staff", { headers: { Authorization: `Bearer ${superTok}` } });
const staff = await r.json();
const cands = staff.filter((s) => s.status === "active" && s.assigned_classes.includes("8th")
  && s.allowed_menus.includes("marks-results") && s.allowed_menus.includes("marks-entry"))
  .sort((a, b) => a.assigned_classes.length - b.assigned_classes.length);
if (!cands.length) { console.log(JSON.stringify({ error: "no active 8th teacher with the marks menus" })); process.exit(0); }
const t = cands[0];
out.teacher = { classes: t.assigned_classes, menus: t.allowed_menus, tempPassword: t.has_temp_password, candidates: cands.length };
const ident = t.email || t.phone;

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.on("console", (m) => { if (m.type() === "error") out.issues.push({ kind: "console", text: m.text().slice(0, 200) }); });
page.on("pageerror", (e) => out.issues.push({ kind: "pageerror", text: String(e).slice(0, 200) }));
page.on("response", (x) => { if (x.status() >= 400 && x.url().includes("/kisschool/")) out.issues.push({ kind: "http", text: `${x.status()} ${x.request().method()} ${x.url().replace(/^.*\/kisschool/, "")}`.slice(0, 200) }); });
const dialogs = [];
page.on("dialog", async (d) => { dialogs.push(d.message().slice(0, 140)); await d.dismiss(); });
const go = async (p) => { await page.goto(`${BASE}${p}`, { waitUntil: "domcontentloaded" }); await page.waitForTimeout(1600); return page.url().replace(BASE, ""); };
const text = async (n = 260) => (await page.locator("main").first().innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, n);
const options = async (trigger) => { await trigger.click(); const o = (await page.getByRole("option").allInnerTexts()).map((s) => s.replace(/\s+/g, " ").trim()); await page.keyboard.press("Escape"); return o; };
const choose = async (trigger, name) => {
  await trigger.click({ timeout: 8000 });
  const opts = page.getByRole("option"); const texts = (await opts.allInnerTexts()).map((s) => s.replace(/\s+/g, " ").trim());
  const k = texts.findIndex((s) => s === name || s.startsWith(name + " ") || s.startsWith(name + "("));
  if (k < 0) { await page.keyboard.press("Escape"); throw new Error(`no option ${name} in [${texts.slice(0, 15).join(" / ")}]`); }
  await opts.nth(k).click(); await page.waitForTimeout(1500);
};

await step("teacher login", async () => {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.fill('input[autocomplete="username"]', ident);
  await page.fill('input[autocomplete="current-password"]', process.env.KIS_PW);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 20000 });
  await page.waitForTimeout(1200);
  return { at: page.url().replace(BASE, ""), menu: (await page.locator("nav").first().innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 200) };
});
await step("results: class list + 8th table", async () => {
  await go("/marks/results");
  const classTrigger = page.locator('[id$="-class"]').first();
  const classes = await options(classTrigger);
  await choose(classTrigger, "8th");
  await page.locator("table").first().waitFor({ timeout: 15000 });
  await page.screenshot({ path: `${SHOTS}/teacher-results.png`, fullPage: true });
  return { classOptions: classes, rows: await page.locator("table").first().locator("tbody tr").count(), scope: (await page.locator('[id$="-scope"]').first().innerText()).trim() };
});
await step("report cards tab (teacher)", async () => {
  await page.getByRole("tab", { name: "Report cards" }).click(); await page.waitForTimeout(1800);
  await page.screenshot({ path: `${SHOTS}/teacher-report-cards.png`, fullPage: true });
  const has = async (re) => (await page.getByText(re).count()) > 0;
  const remarks = page.locator('main input[type="text"], main textarea');
  return {
    cardSettings: await has(/Card settings/), overrides: await has(/^Overrides$/), force: await has(/Force re-render/),
    includeDrafts: await has(/Include draft marks/), generateAll: await has(/Generate all/),
    remarkInputs: await remarks.count(), firstRemarkEditable: (await remarks.count()) ? await remarks.first().isEditable() : null,
  };
});
await step("other class via URL is not shown", async () => {
  const other = ["9th", "10th", "7th", "6th"].find((c) => !t.assigned_classes.includes(c));
  await go(`/marks/results?class=${encodeURIComponent(other)}`);
  return { tried: other, classShown: (await page.locator('[id$="-class"]').first().innerText()).trim(), text: await text(160) };
});
await step("marks entry (teacher)", async () => {
  await go("/marks/entry");
  const combo = page.locator('main button[role="combobox"]');
  const classes = await options(combo.nth(0));
  await choose(combo.nth(0), "8th"); await choose(combo.nth(1), "Mathematics"); await choose(combo.nth(2), "P.T. First");
  const inputs = page.locator('main input[inputmode="numeric"]');
  await page.screenshot({ path: `${SHOTS}/teacher-marks-entry.png` });
  return {
    classOptions: classes, inputs: await inputs.count(), firstDisabled: (await inputs.count()) ? await inputs.first().isDisabled() : null,
    buttons: (await page.locator("main button").allInnerTexts()).map((s) => s.trim()).filter((s) => /save|submit|request|reload/i.test(s)),
    status: (await page.locator("main").innerText()).match(/(Submitted[^.\n]*|Draft[^.\n]*|Locked[^.\n]*|New[^.\n]*)/)?.[0]?.slice(0, 120) ?? "",
  };
});
await step("admin-only pages blocked", async () => {
  const res = {};
  for (const p of ["/templates", "/sessions", "/class-subjects", "/staff", "/reports"]) res[p] = await go(p);
  return res;
});
await step("phone width: results", async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await go("/marks/results");
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${SHOTS}/teacher-mobile-results.png` });
  return { pageOverflowPx: await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth) };
});
out.dialogs = dialogs;
await browser.close();
console.log(JSON.stringify(out, null, 1));
