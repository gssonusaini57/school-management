// Website "Remember me" on TEST: new tab stays signed in, lost access token renews silently, logout ends it.
import { createRequire } from "node:module";
const require = createRequire(process.env.PW_DEPS + "/package.json");
const { chromium } = require("playwright-core");
const BASE = "http://69.62.72.137/kisschool/admin";
const out = { steps: [], issues: [] };
const step = async (name, fn) => { try { out.steps.push({ name, ok: true, info: await fn() }); } catch (e) { out.steps.push({ name, ok: false, error: String(e.message || e).split("\n")[0].slice(0, 200) }); } };
const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } });
const watch = (p, tag) => { p.on("pageerror", (e) => out.issues.push(`${tag}: ${String(e).slice(0, 160)}`)); };
const path = (p) => new URL(p.url()).pathname.replace("/kisschool/admin", "");
const login = async (p, remember) => {
  await p.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await p.fill('input[autocomplete="username"]', process.env.KIS_U1);
  await p.fill('input[autocomplete="current-password"]', process.env.KIS_PW);
  const box = p.locator("#remember"); const on = (await box.getAttribute("data-state")) === "checked";
  if (on !== remember) await box.click();
  await p.click('button[type="submit"]');
  await p.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 20000 }); await p.waitForTimeout(1200);
};
const p1 = await ctx.newPage(); watch(p1, "tab1");
await step("sign in with Remember me", async () => { await login(p1, true); const ck = (await ctx.cookies()).find((c) => c.name === "kis_refresh"); return { at: path(p1), cookie: !!ck, cookiePath: ck && ck.path, httpOnly: ck && ck.httpOnly }; });
const p2 = await ctx.newPage(); watch(p2, "tab2");
await step("new tab opens the dashboard without the login page", async () => {
  await p2.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" }); await p2.waitForTimeout(3500);
  return { at: path(p2), hasToken: await p2.evaluate(() => !!sessionStorage.getItem("kis_token")) };
});
await step("lost access token renews silently on reload", async () => {
  await p2.evaluate(() => sessionStorage.removeItem("kis_token")); await p2.reload({ waitUntil: "domcontentloaded" }); await p2.waitForTimeout(3500);
  return { at: path(p2), hasToken: await p2.evaluate(() => !!sessionStorage.getItem("kis_token")) };
});
await step("Log out ends it: a new tab goes to login", async () => {
  await p2.locator("header button").filter({ hasText: /log ?out/i }).last().click(); await p2.waitForTimeout(2500);
  const p3 = await ctx.newPage(); await p3.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" }); await p3.waitForTimeout(3500);
  return { afterLogout: path(p2), newTab: path(p3), cookieLeft: !!(await ctx.cookies()).find((c) => c.name === "kis_refresh") };
});
const ctx2 = await browser.newContext(); const q1 = await ctx2.newPage(); watch(q1, "noremember");
await step("without Remember me a new tab asks to sign in (as before)", async () => {
  await login(q1, false); const q2 = await ctx2.newPage(); await q2.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" }); await q2.waitForTimeout(3500);
  return { newTab: path(q2), cookie: !!(await ctx2.cookies()).find((c) => c.name === "kis_refresh") };
});
await browser.close();
console.log(JSON.stringify(out, null, 1));
