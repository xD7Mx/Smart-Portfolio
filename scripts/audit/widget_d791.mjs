// ─────────────────────────────────────────────────────────────────────────
// D791 — المالك (2026-11-24): «أريد على الآيفون ويدجت كبقية التطبيقات لتطبيق المحفظة الذكية».
// ويدجت الآيفون الأصيلُ لا يصنعه إلا تطبيقٌ أصيلٌ (‏Xcode على ماك)؛ فالطريقُ الذي يعمل اليوم تطبيقُ «Scriptable» المجانيّ يرسم
// الويدجت من سكربتٍ يُنسخ من الإعدادات ويقرأ ‏/widget/summary برمزٍ يُنشأ هناك. وهذا الحارسُ يقيس الطرفين:
//   أ · بطاقةُ «ويدجت الآيفون» في الإعدادات (الحاسوب فاتحاً وداكناً، والجوال):
//     ١ تُرسم بخطواتها وحالِ الرمز وزرّيها — ٢ «نسخ السكربت» ينسخ سكربتاً بعنوان التطبيق ولا رمزَ فيه —
//     ٣ «إنشاء رمز» يعرض الرمزَ مرّةً بحركة ويُنسخ — ٤ رمزٌ جديد فوق نافذٍ لا يُنشأ بلا تأكيد — ٥ الإلغاءُ يوقفه —
//     ٦ يمينٌ وخطٌّ ≥ 9.5px وهدفُ لمسٍ ≥ 32px بلا فيض — ٧ التباين: أساسيٌّ ≥ 12:1 وثانويٌّ ≥ 4.5:1 — ٨ أرقامٌ لاتينية.
//   ب · السكربتُ المنسوخ نفسُه يُشغَّل في بيئةٍ تحاكي Scriptable (‏ListWidget · Request · Keychain · Alert · FileManager):
//     الرمزُ في ترويسةٍ لا في الرابط، وأرقامُ الملخّص كما هي بأرقامٍ لاتينية، و«غيرُ متوفّر» لا صفر، و‏401 «الرمزُ غيرُ صالح»
//     (وإن لم يكن الجسمُ JSON)، وانقطاعُ الشبكة يعرض آخرَ ملخّصٍ محفوظ، وأوّلُ تشغيلٍ يطلب الرمزَ في حقلٍ سرّيٍّ ويحفظه في
//     سلسلة المفاتيح، وشاشةُ القفل بتخطيطٍ مختصر، وكلُّ خطٍّ ≥ 9.5 وكلُّ لونٍ ≥ 4.5:1 في المظهرين (والثروةُ ≥ 12:1).
//    node scripts/audit/widget_d791.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PORT = 5291;
const ORIGIN = `http://localhost:${PORT}`;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const TOKEN = "spw_" + "Qm7xK2pL9vN4tR8wZ3cY6bH1jF5dS0aE-gU_iO7eWq" + "x9Qz";
const KEY = "smart_portfolio_widget_token";
const NA = "غير متوفّر";

// ═══ ب · المحاكي — يُعرَّف أوّلاً ويُشغَّل على السكربت المنسوخ من البطاقة ═══
const lum = hex => {
  const n = parseInt(hex.replace("#", ""), 16);
  const c = [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const cr = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

class WText { constructor(t) { this.text = t; this.align = "natural"; } rightAlignText() { this.align = "right"; } leftAlignText() { this.align = "left"; } centerAlignText() { this.align = "center"; } }
class WStack {
  constructor() { this.items = []; this.dir = "v"; }
  addText(t) { const x = new WText(t); this.items.push(x); return x; }
  addStack() { const s = new WStack(); this.items.push(s); return s; }
  addSpacer(n) { this.items.push({ spacer: n ?? null }); }
  addImage() { const i = { image: true }; this.items.push(i); return i; }
  layoutHorizontally() { this.dir = "h"; } layoutVertically() { this.dir = "v"; }
  centerAlignContent() {} topAlignContent() {} bottomAlignContent() {} setPadding() {}
}
const texts = (s, out = []) => { for (const it of s?.items || []) { if (it instanceof WText) out.push(it); else if (it.items) texts(it, out); } return out; };

async function runWidget(script, o) {
  const env = { requests: [], alerts: [], files: o.files || {}, keychain: { ...(o.keychain || {}) }, presented: null, widget: null, done: false, logs: [] };
  class Color { constructor(hex) { this.hex = hex; this.light = hex; this.dark = hex; } static dynamic(l, d) { const c = new Color(l.hex); c.dark = d.hex; return c; } }
  const mk = w => s => ({ size: s, weight: w });
  const Font = { systemFont: mk("r"), boldSystemFont: mk("b"), semiboldSystemFont: mk("sb"), mediumSystemFont: mk("m") };
  class ListWidget extends WStack {
    async presentSmall() { env.presented = "small"; env.widget = this; }
    async presentMedium() { env.presented = "medium"; env.widget = this; }
    async presentLarge() { env.presented = "large"; env.widget = this; }
  }
  class Size { constructor(w, h) { this.w = w; this.h = h; } }
  class DateFormatter { string(d) { return new Date(d).toISOString().slice(11, 16); } }
  const Keychain = { contains: k => k in env.keychain, get: k => { if (!(k in env.keychain)) throw new Error("missing"); return env.keychain[k]; },
                     set: (k, v) => { env.keychain[k] = v; }, remove: k => { delete env.keychain[k]; } };
  const answers = [...(o.answers || [])];
  class Alert {
    constructor() { this.fields = []; this.actions = []; env.alerts.push(this); }
    addSecureTextField(p, v) { this.fields.push({ p, v, secure: true }); } addTextField(p, v) { this.fields.push({ p, v, secure: false }); }
    addAction(a) { this.actions.push(a); } addCancelAction(a) { this.cancel = a; }
    async present() { this.answer = answers.shift(); return this.answer == null ? -1 : 0; }
    textFieldValue() { return this.answer; }
  }
  class Request {
    constructor(url) { this.url = url; this.headers = {}; this.method = "GET"; env.requests.push(this); }
    async loadJSON() { const r = o.server(this, env.requests.length); this.response = { statusCode: r.status }; if (r.throw) throw new Error(r.throw); return r.body; }
  }
  const FileManager = { local: () => ({ documentsDirectory: () => "/docs", joinPath: (a, b) => a + "/" + b, fileExists: p => p in env.files,
                                        readString: p => env.files[p], writeString: (p, s) => { env.files[p] = s; } }) };
  const ctx = vm.createContext({
    Color, Font, ListWidget, Size, DateFormatter, Keychain, Alert, Request, FileManager,
    config: { runsInWidget: !!o.inWidget, widgetFamily: o.family }, args: { widgetParameter: o.param ?? null },
    Script: { setWidget: w => { env.widget = w; }, complete: () => { env.done = true; } },
    console: { log: (...a) => env.logs.push(a.join(" ")), error: (...a) => env.logs.push(a.join(" ")), warn: (...a) => env.logs.push(a.join(" ")) },
  });
  try { await vm.runInContext("(async () => {\n" + script + "\n})()", ctx, { timeout: 5000 }); }
  catch (e) { env.error = String(e).split("\n")[0]; }
  return env;
}

const HOLD = [["1120", "الراجحي", -2, 3000], ["2222", "أرامكو", 1, 2750], ["7010", "اس تي سي", 0.4, 900], ["2010", "سابك", -0.8, 800],
              ["1180", "الأهلي", 0.2, 700], ["2280", "المراعي", -0.1, 600], ["4190", "جرير", 1.5, 500]]
  .map(([symbol, name, change_pct, value]) => ({ symbol, name, change_pct, value, weight: 0, currency: "SAR" }));
const DATA = { at: "2026-11-24T10:05:00+00:00", portfolio: "المحفظة الرئيسية", currency: "SAR", wealth: 10500, market_value: 5750, cash: 4750,
               net_profit: 500, return_pct: 9.52, day_change: -34, day_change_pct: -0.59, unrealized: 500, holdings: HOLD, movers: HOLD.slice(0, 3),
               count: 7, tasi: { price: 11500, change_pct: 0.5 } };
const ok200 = d => () => ({ status: 200, body: { success: true, data: d } });

async function scriptSuite(script) {
  if (!script) { say(false, "ب السكربتُ المنسوخ لم يُلتقط — لا يُشغَّل"); return; }
  const API = `${ORIGIN}/api/v1`;
  const all = [];                                       // كلُّ ويدجتٍ رُسم — لفحوص الخطّ واللون والأرقام
  const T = env => { if (env.widget) all.push(env.widget); return texts(env.widget).map(t => t.text); };

  // ١ · في الويدجت، متوسّط، رمزٌ محفوظ
  const s1 = await runWidget(script, { inWidget: true, family: "medium", keychain: { [KEY]: TOKEN }, server: ok200(DATA) });
  const t1 = T(s1), r1 = s1.requests[0] || {};
  const lead = (s1.widget?.items || []).filter(x => x instanceof WText);
  say(!s1.error && r1.url === `${API}/widget/summary` && r1.headers?.["X-Widget-Token"] === TOKEN && !String(r1.url).includes(TOKEN),
      "ب١ السكربتُ يطلب ‏/widget/summary من عنوان التطبيق، والرمزُ في ترويسة ‏X-Widget-Token لا في الرابط", s1.error || r1.url);
  const want1 = ["المحفظة الرئيسية", "إجمالي الثروة", "10,500", "−34  (−0.59%) اليوم", "صافي الربح", "+500", "عائد المحفظة", "+9.52%", "تاسي", "11,500  +0.50%"];
  say(want1.every(w => t1.includes(w)) && lead.length >= 3 && lead.every(x => x.align === "right"),
      "ب٢ المتوسّط: الثروةُ وتغيّرُ اليوم (ريالاً ونسبة) وصافي الربح وعائدُ المحفظة وتاسي — بأرقامٍ لاتينية وإشارةٍ صريحة، والنصُّ يميناً",
      want1.filter(w => !t1.includes(w)).join(" · ") || t1.join(" | "));
  const dayT = texts(s1.widget).find(t => t.text.startsWith("−34")), netT = texts(s1.widget).find(t => t.text === "+500");
  say(dayT?.textColor?.light === "#b91c1c" && netT?.textColor?.light === "#15803d" && dayT?.textColor?.dark === "#f87171" && netT?.textColor?.dark === "#34d399",
      "ب٣ الخسارةُ بلون الخسارة والربحُ بلون الربح في المظهرين", JSON.stringify({ day: dayT?.textColor, net: netT?.textColor }));
  const rf = s1.widget?.refreshAfterDate ? (new Date(s1.widget.refreshAfterDate).getTime() - Date.now()) / 60000 : null;
  const cached = Object.values(s1.files)[0];
  say(s1.widget?.url === `${ORIGIN}/portfolio` && rf != null && rf > 14 && rf <= 15.1 && s1.done && cached && JSON.parse(cached).wealth === 10500,
      "ب٤ الضغطُ يفتح المحفظةَ في التطبيق، والتحديثُ كلَّ ربع ساعة، ويُحفظ آخرُ ملخّصٍ لانقطاع الشبكة", `${s1.widget?.url} · ${rf?.toFixed(1)} دقيقة`);

  // ٢ · الصغير بمعامل all
  const s2 = await runWidget(script, { inWidget: true, family: "small", param: " all ", keychain: { [KEY]: TOKEN }, server: ok200({ ...DATA, portfolio: "كلّ المحافظ" }) });
  const t2 = T(s2), w2 = texts(s2.widget).find(t => t.text === "10,500");
  say(s2.requests[0]?.url === `${API}/widget/summary?pf=all` && t2.includes("كلّ المحافظ") && !t2.includes("تاسي") && w2?.font?.size === 22,
      "ب٥ الصغير: معاملُ ‏all يطلب كلَّ المحافظ، والمحتوى أقلّ (بلا تاسي) والثروةُ أصغر", `${s2.requests[0]?.url} · ${w2?.font?.size}`);

  // ٣ · الكبير: ستُّ حيازاتٍ لا أكثر
  const s3 = await runWidget(script, { inWidget: true, family: "large", keychain: { [KEY]: TOKEN }, server: ok200(DATA) });
  const t3 = T(s3), rows3 = t3.filter(x => /%\s{3}[\d,]+$/.test(x));
  say(t3.includes("الحيازات") && rows3.length === 6 && rows3[0] === "−2.00%   3,000" && t3.some(x => x.includes("الراجحي")),
      "ب٦ الكبير: الحيازاتُ بأسمائها وتغيّرِها وقيمتِها — ستٌّ لا أكثر", rows3.join(" | "));

  // ٤ · ‏401 — بجسمٍ JSON وبغيره
  for (const [lbl, srv] of [["بجسمٍ JSON", () => ({ status: 401, body: { detail: "x" } })], ["بجسمٍ غير JSON", () => ({ status: 401, throw: "JSON parse" })]]) {
    const s = await runWidget(script, { inWidget: true, family: "medium", keychain: { [KEY]: TOKEN }, server: srv });
    const t = T(s);
    say(t.includes("الرمزُ غيرُ صالح") && s.widget?.url === `${ORIGIN}/settings` && s.alerts.length === 0 && s.keychain[KEY] === TOKEN && !t.includes("10,500"),
        `ب٧ ‏401 (${lbl}): «الرمزُ غيرُ صالح» ويفتح الإعدادات — لا أرقامَ قديمةً تُعرض كأنّها حيّة`, t.join(" | "));
  }

  // ٥ · انقطاعُ الشبكة: بمخزنٍ ثمّ بلا مخزن
  const s5 = await runWidget(script, { inWidget: true, family: "medium", keychain: { [KEY]: TOKEN }, files: { ...s1.files }, server: () => ({ status: 0, throw: "offline" }) });
  const t5 = T(s5);
  say(t5.some(x => x.startsWith("آخر تحديث ")) && t5.includes("10,500"), "ب٨ بلا شبكة: آخرُ ملخّصٍ محفوظ موسوماً «آخر تحديث» بوقته", t5.slice(0, 3).join(" | "));
  const s6 = await runWidget(script, { inWidget: true, family: "medium", keychain: { [KEY]: TOKEN }, server: () => ({ status: 0, throw: "offline" }) });
  say(T(s6).includes("تعذّر التحديث"), "ب٩ بلا شبكةٍ ولا مخزن: «تعذّر التحديث» لا أصفار", T(s6).join(" | "));

  // ٦ · بلا رمز
  const s7 = await runWidget(script, { inWidget: true, family: "medium", server: ok200(DATA) });
  say(T(s7).includes("رمزُ الويدجت غيرُ مُدخَل") && s7.requests.length === 0 && s7.alerts.length === 0,
      "ب١٠ في الويدجت بلا رمز: رسالةٌ تدلّ على الخطوة ولا طلبَ بلا رمز", T(s7).join(" | "));

  // ٧ · أوّلُ تشغيلٍ في Scriptable: يطلب الرمزَ في حقلٍ سرّيّ ويحفظه
  const s8 = await runWidget(script, { inWidget: false, answers: [TOKEN], server: ok200(DATA) });
  const a8 = s8.alerts[0];
  say(s8.alerts.length === 1 && a8?.fields?.[0]?.secure && s8.keychain[KEY] === TOKEN && s8.requests[0]?.headers?.["X-Widget-Token"] === TOKEN && s8.presented === "medium",
      "ب١١ أوّلُ تشغيلٍ في Scriptable: يطلب الرمزَ في حقلٍ سرّيّ، ويحفظه في سلسلة مفاتيح الآيفون، ويعرض المعاينة", JSON.stringify({ alerts: s8.alerts.length, presented: s8.presented }));
  const s9 = await runWidget(script, { inWidget: false, keychain: { [KEY]: "spw_old" }, answers: [TOKEN],
                                       server: req => req.headers["X-Widget-Token"] === TOKEN ? { status: 200, body: { success: true, data: DATA } } : { status: 401, body: {} } });
  say(s9.alerts.length === 1 && s9.requests.length === 2 && s9.keychain[KEY] === TOKEN && T(s9).includes("10,500"),
      "ب١٢ رمزٌ مُلغى في Scriptable: يُطلب الجديدُ مرّةً ويُعاد الطلبُ به", JSON.stringify({ alerts: s9.alerts.length, req: s9.requests.length }));

  // ٨ · ما لا مصدرَ له «غيرُ متوفّر» لا صفر
  const s10 = await runWidget(script, { inWidget: true, family: "medium", keychain: { [KEY]: TOKEN },
                                        server: ok200({ ...DATA, net_profit: null, return_pct: null, day_change: null, day_change_pct: null, tasi: null }) });
  const t10 = T(s10);
  say(t10.filter(x => x === NA).length >= 4 && !t10.some(x => /^[+−]?0(\.00)?%?$/.test(x)),
      "ب١٣ ما لا مصدرَ له «غيرُ متوفّر» — لا صفرٌ مكانه (صافي الربح، العائد، تغيّرُ اليوم، تاسي)", t10.join(" | "));

  // ٩ · شاشةُ القفل (‏accessory*): مساحةٌ صغيرة — لا يُحشر فيها تخطيطُ الشاشة الرئيسية
  const acc = (family, server, files) => runWidget(script, { inWidget: true, family, keychain: { [KEY]: TOKEN }, files, server });
  const sa = await acc("accessoryRectangular", ok200(DATA)), si = await acc("accessoryInline", ok200(DATA)), sc = await acc("accessoryCircular", ok200(DATA));
  const sx = await acc("accessoryRectangular", () => ({ status: 401, body: {} }));
  const ss = await acc("accessoryRectangular", () => ({ status: 0, throw: "offline" }), { ...s1.files });
  const ta = T(sa), ti = T(si), tc = T(sc), tx = T(sx), ts = T(ss);
  say(ta.join("|") === "المحفظة الرئيسية|10,500|−34 (−0.59%) اليوم" && texts(sa.widget).every(x => x.align === "right")
      && ti.join("|") === "الثروة 10,500 · −0.59% اليوم" && tc.join("|") === "اليوم|−0.59%"
      && tx.includes("الرمزُ غيرُ صالح") && !tx.includes("10,500") && ts[0]?.startsWith("آخر تحديث ") && ts.includes("10,500") && sa.widget?.url === `${ORIGIN}/portfolio`,
      "ب١٤ شاشةُ القفل: المستطيلُ (المحفظة · الثروة · تغيّرُ اليوم) والسطرُ والدائرة — ورسائلُ الرمز والانقطاع مختصرة",
      [ta.join("|"), ti.join("|"), tc.join("|"), tx.join("|"), ts.join("|")].join(" ‖ "));

  // ١٠ · عبر كلّ ما رُسم: الخطّ واللون والأرقام والرمز
  const allT = all.flatMap(w => texts(w));
  const minF = Math.min(...allT.map(t => t.font?.size ?? 99));
  const bgs = all.map(w => w.backgroundColor).filter(Boolean);
  const worst = Math.min(...allT.flatMap(t => bgs.slice(0, 1).flatMap(bg => [cr(t.textColor.light, bg.light), cr(t.textColor.dark, bg.dark)])));
  const wealthT = allT.filter(t => t.text === "10,500");
  const wealthMin = Math.min(...wealthT.flatMap(t => [cr(t.textColor.light, bgs[0].light), cr(t.textColor.dark, bgs[0].dark)]));
  say(minF >= 9.5 && worst >= 4.5 && wealthMin >= 12 && bgs.every(b => b.light === "#ffffff" && b.dark === "#0d0d0d"),
      "ب١٥ كلُّ خطٍّ ≥ 9.5 وكلُّ لونٍ ≥ 4.5:1 على الخلفية في المظهرين، والثروةُ ≥ 12:1 — من رموز التطبيق",
      `أصغرُ خطّ ${minF} · أدنى تباين ${worst.toFixed(2)} · الثروة ${wealthMin.toFixed(2)}`);
  const indic = allT.filter(t => /[٠-٩۰-۹]/.test(t.text)).map(t => t.text);
  const leak = allT.some(t => t.text.includes(TOKEN)) || [s1, s2, s3, s5, s8, s9].some(s => s.logs.some(l => l.includes(TOKEN)));
  say(indic.length === 0 && !leak && !/console\.log/.test(script), "ب١٦ الأرقامُ لاتينيةٌ كلُّها، والرمزُ لا يظهر في الويدجت ولا يُطبع", indic.join(" · "));
}

// ═══ أ · البطاقة في الإعدادات ═══
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`${ORIGIN}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const SHOTS = process.env.SHOTS;
let copiedScript = null;
const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب · فاتح", { width: 1366, height: 900 }, "light"], ["الحاسوب · داكن", { width: 1366, height: 900 }, "dark"],
                                  ["الجوال · فاتح", { width: 390, height: 844 }, "light"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  let state = { active: false, hint: null, created: null, used: null };
  const calls = { post: 0, del: 0 };
  let confirmAnswer = true, dialogs = 0;
  page.on("dialog", d => { dialogs += 1; (confirmAnswer ? d.accept() : d.dismiss()).catch(() => {}); });
  await page.addInitScript(() => {
    try {
      localStorage.setItem("sp_token", "probe");
      window.__copied = [];
      Object.defineProperty(navigator, "clipboard", { configurable: true,
        value: { writeText: async t => { window.__copied.push(String(t)); }, readText: async () => window.__copied.at(-1) || "" } });
    } catch { /* */ }
  });
  await page.route("**/api/v1/**", async r => {
    const req = r.request(), u = new URL(req.url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = req.method();
    if (p === "/widget/token") {
      if (m === "POST") { calls.post += 1; state = { active: true, hint: TOKEN.slice(-4), created: new Date().toISOString(), used: null };
                          return r.fulfill(body({ token: TOKEN, hint: state.hint, created: state.created })); }
      if (m === "DELETE") { calls.del += 1; state = { active: false, hint: null, created: null, used: null }; return r.fulfill(body({ active: false })); }
      return r.fulfill(body(state));
    }
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    if (p.includes("project-start")) return r.fulfill(body({ start: "2024-03-15" }));
    return r.fulfill(body([]));
  });
  await page.goto(`${ORIGIN}/settings`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.locator("nav button[aria-pressed]", { hasText: "ويدجت الآيفون" }).first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(700);
  const card = page.locator('[data-role="widget-card"]');
  if (!(await card.count())) { say(false, `${label}: بطاقةُ «ويدجت الآيفون» لم تُرسم في الإعدادات`); await ctx.close(); continue; }
  const txt = sel => page.locator(sel).first().innerText().catch(() => "");
  const steps = await page.locator('[data-role="widget-steps"] li').count();
  say((await txt('[data-role="widget-card"] h2')) === "ويدجت الآيفون" && (await txt('[data-role="widget-status"]')) === "لا رمز" && steps === 5
      && await page.locator('[data-role="widget-copy-script"]').isVisible() && await page.locator('[data-role="widget-create"]').isVisible()
      && (await page.locator('[data-role="widget-revoke"]').count()) === 0,
      `${label}: ١ البطاقةُ في الإعدادات بخطواتها الخمس وحالِ الرمز «لا رمز» وزرَّي النسخ والإنشاء`, `${steps} خطوات`);

  // ٢ · نسخُ السكربت
  await page.locator('[data-role="widget-copy-script"]').click();
  await page.waitForTimeout(250);
  const sc = await page.evaluate(() => window.__copied.at(-1) || "");
  const scOk = sc.includes(`const ORIGIN = "${ORIGIN}";`) && sc.includes(`const API = "${ORIGIN}/api/v1";`) && sc.includes('"X-Widget-Token": t')
    && !sc.includes("__ORIGIN__") && !sc.includes("__API__") && !sc.replace('"spw_…"', "").includes("spw_");
  say(scOk && (await txt('[data-role="widget-copy-script"]')).includes("نُسخ السكربت"),
      `${label}: ٢ «نسخ سكربت الويدجت» ينسخ سكربتاً بعنوان هذا التطبيق — ولا رمزَ فيه — ويقول «نُسخ السكربت»`, `${sc.length} حرفاً`);
  if (scOk && !copiedScript) copiedScript = sc;

  // ٣ · إنشاءُ الرمز
  await page.locator('[data-role="widget-create"]').click();
  await page.waitForTimeout(600);
  const tokVal = await txt('[data-role="widget-token-val"]');
  const anim = await page.evaluate(() => { const e = document.querySelector('[data-role="widget-token"]'); return e ? getComputedStyle(e).animationName : null; });
  const st1 = await txt('[data-role="widget-status"]');
  await page.locator('[data-role="widget-copy-token"]').click().catch(() => {});
  await page.waitForTimeout(200);
  const copiedTok = await page.evaluate(() => window.__copied.at(-1) || "");
  say(calls.post === 1 && dialogs === 0 && tokVal === TOKEN && anim && anim !== "none" && st1.includes("نافذ") && st1.includes(TOKEN.slice(-4))
      && copiedTok === TOKEN && (await txt('[data-role="widget-create"]')).includes("رمزٌ جديد") && await page.locator('[data-role="widget-revoke"]').isVisible(),
      `${label}: ٣ «إنشاء رمز» يعرض الرمزَ مرّةً بحركةٍ ويُنسخ، والحالُ «نافذ · ينتهي بـ ${TOKEN.slice(-4)}» ويظهر «إلغاء الرمز»`,
      JSON.stringify({ post: calls.post, anim, st1 }));

  // ٦ · ٧ · ٨ — والرمزُ ظاهر (أكثرُ البطاقة امتلاءً)
  if (SHOTS) await card.screenshot({ path: join(SHOTS, `d791_widget_${vp.width}_${theme}.png`) }).catch(() => {});
  const m = await page.evaluate(() => {
    const cardEl = document.querySelector('[data-role="widget-card"]');
    const parse = s => {
      let v = s.match(/rgba?\(([^)]+)\)/);
      if (v) { const a = v[1].split(/[,\s/]+/).filter(Boolean).map(Number); return [a[0], a[1], a[2], a.length > 3 ? a[3] : 1]; }
      v = s.match(/color\(srgb ([^)]+)\)/);
      if (v) { const a = v[1].split(/[\s/]+/).filter(Boolean).map(Number); return [a[0] * 255, a[1] * 255, a[2] * 255, a.length > 3 ? a[3] : 1]; }
      return [0, 0, 0, 0];
    };
    const L = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
    const ratio = (a, b) => { const [x, y] = [L(a), L(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
    const bgsOf = el => {                                  // الخلفيةُ الفعلية: من أوّل طبقةٍ معتمة (لونٍ أو تدرّج) صعوداً، وكلُّ محطّةِ تدرّجٍ مرشَّحة
      const layers = [];
      let base = null;
      for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e), c = parse(cs.backgroundColor), gi = cs.backgroundImage || "";
        if (gi.includes("gradient")) {
          const stops = [...gi.matchAll(/rgba?\([^)]+\)|color\(srgb [^)]+\)/g)].map(x => parse(x[0]).slice(0, 3));
          if (stops.length) { base = stops; break; }
        }
        if (c[3] > 0) { if (c[3] >= 0.999) { base = [c.slice(0, 3)]; break; } layers.push(c); }
      }
      if (!base) { const b = parse(getComputedStyle(document.body).backgroundColor), h = parse(getComputedStyle(document.documentElement).backgroundColor);
                   base = [b[3] > 0 ? b.slice(0, 3) : h[3] > 0 ? h.slice(0, 3) : [255, 255, 255]]; }
      return base.map(b0 => { let out = b0; for (let i = layers.length - 1; i >= 0; i--) { const [r, g, b, a] = layers[i];
                                out = [r * a + out[0] * (1 - a), g * a + out[1] * (1 - a), b * a + out[2] * (1 - a)]; } return out; });
    };
    const leaves = [...cardEl.querySelectorAll("*")].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && e.getClientRects().length);
    const rows = leaves.map(e => {
      const cs = getComputedStyle(e), fg = parse(cs.color);
      const c = Math.min(...bgsOf(e).map(bg => ratio([fg[0] * fg[3] + bg[0] * (1 - fg[3]), fg[1] * fg[3] + bg[1] * (1 - fg[3]), fg[2] * fg[3] + bg[2] * (1 - fg[3])], bg)));
      return { t: e.textContent.trim().slice(0, 24), tag: e.tagName, fs: parseFloat(cs.fontSize), dir: cs.direction, ta: cs.textAlign,
               cr: +c.toFixed(2), primary: e.closest("h2, [data-role='widget-steps']") !== null };
    });
    const btns = [...cardEl.querySelectorAll("button")].map(b => { const r = b.getBoundingClientRect(); return { h: r.height, w: r.width }; });
    const blocks = [...cardEl.querySelectorAll("h2, p, li")].map(e => ({ dir: getComputedStyle(e).direction, ta: getComputedStyle(e).textAlign }));
    const W = document.documentElement.clientWidth;
    return { rows, btns, blocks, over: Math.max(document.documentElement.scrollWidth - W, cardEl.scrollWidth - cardEl.clientWidth),
             text: cardEl.innerText };
  });
  const minFs = Math.min(...m.rows.map(r => r.fs)), minBtn = Math.min(...m.btns.map(b => Math.min(b.h, b.w)));
  say(m.blocks.every(b => b.dir === "rtl" && (b.ta === "start" || b.ta === "right")) && minFs >= 9.5 && minBtn >= 32 && m.over <= 1,
      `${label}: ٦ يمينٌ كلُّه، وأصغرُ خطّ ≥ 9.5px، وأصغرُ هدفِ لمسٍ ≥ 32px، بلا فيضٍ أفقيّ`, `خطّ ${minFs}px · زرّ ${minBtn.toFixed(0)}px · فيض ${m.over}`);
  const weakP = m.rows.filter(r => r.primary && r.cr < 12), weak = m.rows.filter(r => r.cr < 4.5);
  say(weakP.length === 0 && weak.length === 0, `${label}: ٧ التباين: الأساسيُّ (العنوانُ والخطوات) ≥ 12:1 وكلُّ نصٍّ ≥ 4.5:1`,
      JSON.stringify([...weakP, ...weak].slice(0, 3)));
  say(!/[٠-٩۰-۹]/.test(m.text), `${label}: ٨ الأرقامُ لاتينيةٌ في البطاقة`);

  // ٤ · رمزٌ جديدٌ فوق نافذ: لا يُنشأ بلا تأكيد
  confirmAnswer = false;
  await page.locator('[data-role="widget-create"]').click();
  await page.waitForTimeout(400);
  say(dialogs === 1 && calls.post === 1 && (await txt('[data-role="widget-token-val"]')) === TOKEN,
      `${label}: ٤ «رمزٌ جديد» فوق رمزٍ نافذ يسأل أوّلاً — ورفضُ السؤال لا يُبطل الحاليّ`, JSON.stringify({ dialogs, post: calls.post }));

  // ٥ · الإلغاء
  confirmAnswer = true;
  await page.locator('[data-role="widget-revoke"]').click();
  await page.waitForTimeout(600);
  say(dialogs === 2 && calls.del === 1 && (await txt('[data-role="widget-status"]')) === "لا رمز" && (await page.locator('[data-role="widget-token"]').count()) === 0
      && (await page.locator('[data-role="widget-revoke"]').count()) === 0,
      `${label}: ٥ «إلغاء الرمز» بعد تأكيدٍ يوقفه: «لا رمز» ويختفي الرمزُ المعروض`, JSON.stringify({ dialogs, del: calls.del }));
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();

await scriptSuite(copiedScript);
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
