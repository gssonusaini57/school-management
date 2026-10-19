// Marks Entry browser check on TEST (no saves). Login from env vars only.
import { createRequire } from "node:module";
const require = createRequire(process.env.PW_DEPS + "/package.json");
const { chromium } = require("playwright-core");
const BASE = "http://69.62.72.137/kisschool/admin";
const out = {}; const issues = [];
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
page.on("pageerror", (e) => issues.push(String(e).slice(0, 200)));
page.on("console", (m) => { if (m.type() === "error") issues.push(m.text().slice(0, 200)); });
const dialogs = [];
page.on("dialog", async (d) => { dialogs.push(d.message().slice(0, 160)); await d.dismiss(); });
try {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.fill('input[autocomplete="username"]', process.env.KIS_U1);
  await page.fill('input[autocomplete="current-password"]', process.env.KIS_PW);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 20000 });
  await page.goto(`${BASE}/marks/entry`, { waitUntil: "domcontentloaded" }); await page.waitForTimeout(1500);
  const combo = page.locator('main button[role="combobox"]');
  const choose = async (i, name) => {
    await combo.nth(i).click({ timeout: 8000 });
    const opts = page.getByRole("option");
    const texts = (await opts.allInnerTexts()).map((t) => t.replace(/\s+/g, " ").trim());
    const k = texts.findIndex((t) => t === name || t.startsWith(name + " ") || t.startsWith(name + "("));
    if (k < 0) { await page.keyboard.press("Escape"); throw new Error(`no option ${name} in [${texts.slice(0, 12).join(" / ")}]`); }
    await opts.nth(k).click(); await page.waitForTimeout(1500);
  };
  await choose(0, "8th"); await choose(1, "Mathematics"); await choose(2, "P.T. First");
  const inputs = page.locator('main input[inputmode="numeric"]');
  out.studentInputs = await inputs.count();
  out.firstValue = await inputs.first().inputValue();
  out.firstDisabled = await inputs.first().isDisabled();
  out.buttons = (await page.locator("main button").allInnerTexts()).map((s) => s.trim()).filter((s) => /save|submit|request|reload/i.test(s));
  out.banner = (await page.locator('main [role="status"], main [role="alert"]').allInnerTexts()).join(" | ").replace(/\s+/g, " ").slice(0, 300);
  if (!out.firstDisabled && out.studentInputs) {
    const orig = out.firstValue;
    await inputs.first().fill("");
    await inputs.first().pressSequentially("12.5");
    out.afterTyping12_5 = await inputs.first().inputValue();
    await choose(0, "7th").catch((e) => { out.switchError = String(e.message).split("\n")[0]; });
    out.dialogOnSwitch = dialogs.slice();
    out.classAfterDismiss = (await combo.nth(0).innerText()).trim();
    await inputs.first().fill(orig);          // back to the saved value; nothing is saved
    out.restored = (await inputs.first().inputValue()) === orig;
  }
  await page.screenshot({ path: `${process.env.SHOTS}/marks-entry.png`, fullPage: false });
} catch (e) { out.error = String(e.message || e).split("\n")[0]; }
out.issues = issues;
console.log(JSON.stringify(out, null, 1));
await browser.close();
