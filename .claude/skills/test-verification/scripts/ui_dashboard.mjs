// Web dashboard check on TEST: admin pie + lists, class-wise chart; teacher sees only the chart. No saves.
import { createRequire } from "node:module";
const require = createRequire(process.env.PW_DEPS + "/package.json");
const { chromium, request } = require("playwright-core");
const ORIGIN = "http://69.62.72.137"; const BASE = `${ORIGIN}/kisschool/admin`; const SHOTS = process.env.SHOTS;
const out = { steps: [], issues: [] };
const step = async (name, fn) => { try { out.steps.push({ name, ok: true, info: await fn() }); } catch (e) { out.steps.push({ name, ok: false, error: String(e.message || e).split("\n")[0].slice(0, 220) }); } };
const api = await request.newContext({ baseURL: `${ORIGIN}/kisschool/api/` });
let r = await api.post("auth/login", { data: { identifier: process.env.KIS_U1, password: process.env.KIS_PW } });
const sup = (await r.json()).token;
const staff = await (await api.get("staff", { headers: { Authorization: `Bearer ${sup}` } })).json();
const t = staff.find((s) => s.status === "active" && s.assigned_classes.includes("8th"));
const browser = await chromium.launch({ channel: "chrome", headless: true });
async function session(ident, tag) {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
  page.on("console", (m) => { if (m.type() === "error") out.issues.push(`${tag}: ${m.text().slice(0, 180)}`); });
  page.on("pageerror", (e) => out.issues.push(`${tag}: ${String(e).slice(0, 180)}`));
  page.on("response", (x) => { if (x.status() >= 400 && x.url().includes("/kisschool/")) out.issues.push(`${tag}: ${x.status()} ${x.url().replace(/^.*\/kisschool/, "")}`); });
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.fill('input[autocomplete="username"]', ident);
  await page.fill('input[autocomplete="current-password"]', process.env.KIS_PW);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 20000 });
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" }); await page.waitForTimeout(2500);
  return page;
}
const p = await session(process.env.KIS_U1, "super");
await step("super-admin: pie card + chart present", async () => {
  await p.screenshot({ path: `${SHOTS}/super-dashboard.png`, fullPage: true });
  const txt = (await p.locator("main").innerText()).replace(/\s+/g, " ");
  return { pieCard: /Pending/.test(txt) && /Marked/.test(txt), chartCard: /Class-wise attendance/.test(txt), canvases: await p.locator("main canvas").count() };
});
await step("super-admin: Pending opens the class list, Back returns", async () => {
  const btn = p.getByRole("button", { name: /Pending/ }).first();
  await btn.click(); await p.waitForTimeout(1200);
  const url1 = p.url(); const listTxt = (await p.locator("main").innerText()).replace(/\s+/g, " ");
  await p.screenshot({ path: `${SHOTS}/super-pending-list.png`, fullPage: true });
  await p.goBack(); await p.waitForTimeout(1200);
  return { openedUrl: url1.replace(BASE, ""), listShowsClasses: (listTxt.match(/\b(Nursery|L\.K\.G|8th|12th)\b/g) || []).length, backUrl: p.url().replace(BASE, "") };
});
await step("super-admin: chart This month", async () => {
  await p.getByRole("button", { name: /This month/ }).first().click(); await p.waitForTimeout(2500);
  await p.screenshot({ path: `${SHOTS}/super-chart-month.png`, fullPage: true });
  return { title: ((await p.locator("main").innerText()).match(/Class-wise attendance[^\n]*/) || [""])[0].slice(0, 80) };
});
const tp = await session(t.email || t.phone, "teacher");
await step("teacher: chart only, no pie", async () => {
  await tp.screenshot({ path: `${SHOTS}/teacher-dashboard.png`, fullPage: true });
  const txt = (await tp.locator("main").innerText()).replace(/\s+/g, " ");
  return { chartCard: /Class-wise attendance/.test(txt), pieCard: /Class attendance today/.test(txt) };
});
await browser.close();
console.log(JSON.stringify(out, null, 1));
