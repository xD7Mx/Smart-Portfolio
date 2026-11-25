// ─────────────────────────────────────────────────────────────────────────
// D838 — فرصةُ صقر والتحليلُ الذكيّ على السهم نفسِه لا يتناقضان (المالك 2026-11-25): «في الفرص وجدتُ فرصةً — ATR — رشّحت عقداً، ووضعتُ في
// التحليل الذكيّ ميزانيةً 200 فأخبرني أنّه لا توجد فرص… ربكة»؛ و«ألغِ علامةَ الدولار بجانب الميزانية».
// قيس على الخادم (‏opp_vs_advice_door_d838): «الأنسب» في دليل الفرصة عقدُ Call 130 بلا عرضٍ ولا طلبٍ واهتمامُه المفتوح صفر — سُعّر بآخر صفقة؛
// والتحليلُ الذكيّ فحص ستّةَ عشرَ عقداً ورفضها كلَّها محقّاً، بلا سبب («لا عقدَ مقبولاً ضمن هذه الشروط»).
//  ١ عقودُ نطاق الفرصة بلا تداولٍ فعليّ: لا يُرشَّح منها شيء، ويقول الدليلُ ذلك ولماذا — والفرصةُ على السهم نفسِه.
//  ٢ وعقودٌ تُتداول (عرضٌ وطلبٌ وفارقٌ ضيّقٌ واهتمام): يُرشَّح «الأنسب» منها كما كان.
//  ٣ التحليلُ الذكيّ من الفرصة يحلّل الفرصةَ نفسَها: جهتَها (‏call) وأقصرَ أجلٍ يتّسع لمدّتها (‏75 يوماً لشهرين) وميزانيةَ المالك — وسببُ «لا شيء» معروض.
//  ٤ الميزانيةُ بلا علامة الدولار بجانبها.
//    node scripts/audit/opp_advice_d838.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5338;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const COUNCIL = { verdict: "يوافق", score: 100, veto: false, oks: 7, warns: 0, members: [] };
const OPP = { symbol: "ATR", name: "AptarGroup", setup: "ارتدادٌ من منطقة الوسط", side: "long", quality: 70, horizon: "شهران", horizon_n: 2,
  entry: [98, 101], target: 120, stop: 92, rr: 2.3, zone: "الوسط", where: "في منطقة الوسط", close: 100, trend: { word: "صاعد", level: "قويّ", strength: 62 },
  liq: { word: "داخلة", level: "متوسّطة", strength: 48, tag: null }, k: 18, rsi: 50, weekly: "صاعد", reasons: [], council: COUNCIL };
const OPPS = { market: "us", at: iso(now - 3600e3), universe: 800, screened: 790, read: 150, found: 1, min_q: 50, job: { on: false, msg: "", at: null }, rejected: [], items: [OPP] };
const EXPS = [[1, "2026-12-18", 23], [2, "2027-01-15", 51], [3, "2027-02-19", 86], [4, "2027-05-21", 177]].map(([t, date, dte]) => ({ t, date, dte }));
const CALL = { 80: [21.5, .93], 85: [17, .88], 90: [12.8, .8], 95: [9, .68], 100: [6, .55], 105: [3.8, .42], 110: [2.2, .3], 115: [1.2, .2], 120: [0.7, .13] };
const occ = (date, cp, k) => `ATR${date.slice(2, 4)}${date.slice(5, 7)}${date.slice(8, 10)}${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
let DEAD = true;
const chain = t => { const e = EXPS.find(x => x.t === t) || EXPS[0];
  const row = (k, cp) => { const [a, d] = CALL[k]; const put = cp === "P";
    const live = !DEAD;
    return { contract: occ(e.date, cp, k), strike: k, last: a, bid: live ? a - 0.1 : 0, ask: live ? a : 0, pct: 0, volume: live ? 500 : 5, oi: live ? 2000 : 0, iv: 40, itm: put ? k > 100 : k < 100,
      g: live ? { iv: 40, delta: put ? -(1 - d) : d, gamma: 0.02, theta: -0.02, vega: 0.1, itm: d, pop: 0.4, px: a, src: "ask", spread: 2, be: k + a } : null }; };
  const ks = Object.keys(CALL).map(Number);
  return { symbol: "ATR", name: "AptarGroup", price: 100, expirations: EXPS, expiry: e.t, calls: ks.map(k => row(k, "C")), puts: ks.map(k => row(k, "P")),
    stats: { atm_iv: 40, move: 6, move_pct: 6, pcr_vol: 0.8, pcr_oi: 0.9, max_pain: 100, vol: { call: 10, put: 8 }, oi: { call: 0, put: 0 } }, session: SES }; };
const ST = { market: "us", ccy: "USD", on: true, capital: 1000, goal: 100000, cash: 1000, equity: 1000, pl: 0, pl_pct: 0, progress: 0, started: iso(now - 86400e3),
  tier: { frac: 0.25, seats: 4 }, positions: [], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0, today: { wins: 0, losses: 0, realized: 0, new: 0 },
  exposure: { contracts: 0, cost: 0, value: 0, ret: null }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 1000]], signals: [], log: [], gates: [], scan: null, session: null,
  last_cycle: null, last_check: null, health: {}, broker: { linked: false, name: "IBKR" }, runs: [], running: { on: false, msg: "", at: null },
  settings: { opt_stop: 40, stock_stop: 6, take_x: 2, mode: "balanced", auto: false, sides: "both", instruments: "both" }, day: null, orders: [], pulse: null, geo: null,
  rules: { stop: 0.6, take: 2, growth: 15 }, regime: null, opps: { at: OPPS.at, universe: 800, screened: 790, read: 150, found: 1 } };
const NONE = "فُحص 16 عقداً على ATR: 16 بلا عرضٍ وطلبٍ حيّين — عقودُه لا تصلح للتداول الآن، والفرصةُ على السهم نفسِه.";

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp] of [["الحاسوب", { width: 1366, height: 900 }], ["الجوال", { width: 390, height: 844 }]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [], adv = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_saqr_tab", "opps"); localStorage.setItem("sp_saqr_market", "us");
    localStorage.removeItem("sp_oc_budget"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "ATR", price: 100, change: 0.4, change_pct: 0.4, time: new Date().toISOString(), delayed: 0, session: SES }));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa" } }));
    if (p === "/market/saqr") return r.fulfill(body(ST));
    if (p === "/market/saqr/opportunities") return r.fulfill(body(OPPS));
    if (p.startsWith("/market/options/")) return r.fulfill(body(chain(Number(u.searchParams.get("date")) || 1)));
    if (p === "/market/options-advice") { adv.push(Object.fromEntries(u.searchParams));
      return r.fulfill(body({ symbol: "ATR", price: 100, best: [], refused: [], fit: { ok: false, min_cost: null, text: NONE }, budget: 200, scanned: 16, abstain: null, lean: "call" })); }
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  const open = async () => {
    await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await sleep(1400);
    await page.locator('[data-role="sq-nav"] [data-view="opps"]').click().catch(() => {}); await sleep(900);
    await page.locator('[data-role="so-chain"]').first().click().catch(() => {}); await sleep(1600);
  };
  const guideOf = () => page.evaluate(() => ({ guide: !!document.querySelector('[data-role="oc-guide"]'), exp: document.querySelector('[data-role="oc-exp"].on')?.textContent || "",
    dead: document.querySelector('[data-role="oc-guide-dead"]')?.textContent || "", picks: document.querySelectorAll('[data-role="oc-guide-code"]').length }));

  // ═ ١ عقودٌ لا تُتداول ═
  DEAD = true;
  await open();
  const g1 = await guideOf();
  say(g1.guide && g1.picks === 0 && /لا تُتداول فعلاً/.test(g1.dead) && /على السهم نفسِه/.test(g1.dead),
    `${label}: ١ عقودُ نطاق الفرصة بلا عرضٍ وطلبٍ ولا اهتمام: لا يُرشَّح منها شيء، والدليلُ يقول ذلك ولماذا — والفرصةُ على السهم نفسِه`, JSON.stringify(g1));

  // ═ ٣ · ٤ التحليلُ الذكيّ من الفرصة، والميزانيةُ بلا علامة الدولار ═
  const lbl = (await page.locator(".ocx-budget > span").first().textContent().catch(() => "")) || "";
  await page.locator('[data-role="oc-budget"]').fill("200").catch(() => {});
  await page.locator('[data-role="oc-smart"]').click().catch(() => {}); await sleep(1300);
  const fit = (await page.locator('[data-role="oc-fit"]').textContent().catch(() => "")) || "";
  const q = adv[adv.length - 1] || {};
  say(q.symbol === "ATR" && q.side === "call" && q.min_dte === "75" && q.budget === "200" && /بلا عرضٍ وطلبٍ حيّين/.test(fit),
    `${label}: ٣ التحليلُ الذكيّ من الفرصة يحلّل الفرصةَ نفسَها — جهتَها وأقصرَ أجلٍ يتّسع لمدّتها (75 يوماً لشهرين) وميزانيةَ المالك — وسببُ «لا شيء» معروضٌ بالأعداد`,
    JSON.stringify({ q, fit: fit.slice(0, 90) }));
  say(lbl.trim() === "الميزانية" && !/\$/.test(lbl), `${label}: ٤ الميزانيةُ بلا علامة الدولار بجانبها`, JSON.stringify(lbl));

  // ═ ٢ عقودٌ تُتداول ═
  DEAD = false;
  await open();
  const g2 = await guideOf();
  say(g2.guide && g2.picks >= 1 && !g2.dead, `${label}: ٢ وعقودٌ تُتداول (عرضٌ وطلبٌ وفارقٌ ضيّقٌ واهتمام): يُرشَّح «الأنسب» منها كما كان`, JSON.stringify(g2));
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
