// ─────────────────────────────────────────────────────────────────────────
// D800 — المالك (2026-11-24): «أريد في الويدجت الشركاتِ اللي حاطّها في القائمة — مثل ويدجت تريدنق فيو: عشرُ شركاتٍ أو أكثر، مقاسَ منتصف شاشة
// الآيفون تقريباً، تتوزّع على اليمين وعلى اليسار». سكربتُ Scriptable نفسُه (من ‏widgetScript.ts كما يُنسخ) يُشغَّل في محاكيه بخانة ‏list:
//   ١ ‏list ⇒ ‏/widget/watchlist بلا اسم، و‏list:اسم ⇒ القائمةُ باسمها — والرمزُ في الترويسة.
//   ٢ عمودان من اليمين: الأوّلُ يمينٌ والثاني يساره، ولكلٍّ شعارٌ ورمزٌ واسمٌ وسعرٌ وتغيّرٌ بلونه — والكبيرُ ستّةَ عشر والمتوسّطُ ستّة والصغيرُ ثلاثة،
//      وما زاد «+N».
//   ٣ الشعارُ من بابنا العامّ ويُحفظ في الجهاز (لا يُعاد جلبُه في التحديث التالي)، وما تعذّر شعارُه دائرةٌ بحرفه.
//   ٤ ما لا سعرَ له «غير متوفّر» لا صفر، والأرقامُ لاتينية، وكلُّ خطٍّ ≥ 9.5، وقائمةٌ لا وجودَ لها «القائمةُ غيرُ موجودة»، وشاشةُ القفل مختصرة.
//    node scripts/audit/widget_d800.mjs
// ─────────────────────────────────────────────────────────────────────────
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const ts = readFileSync(join(ROOT, "frontend/src/lib/widgetScript.ts"), "utf8");
const m = /const SCRIPT = String\.raw`([\s\S]*?)`;\n/.exec(ts);
if (!m) { say(false, "٠ السكربتُ لم يُستخرج من widgetScript.ts"); process.exit(1); }
const ORIGIN = "https://app.example";
const script = m[1].replace("__ORIGIN__", JSON.stringify(ORIGIN)).replace("__API__", JSON.stringify(ORIGIN + "/api/v1"));
const TOKEN = "spw_" + "x".repeat(43), KEY = "smart_portfolio_widget_token";

class WText { constructor(t) { this.text = t; this.align = "natural"; } rightAlignText() { this.align = "right"; } leftAlignText() {} centerAlignText() {} }
class WImage { constructor(img) { this.image = img; } }
class WStack {
  constructor() { this.items = []; }
  addText(t) { const x = new WText(t); this.items.push(x); return x; }
  addStack() { const s = new WStack(); this.items.push(s); return s; }
  addSpacer(n) { this.items.push({ spacer: n ?? null }); }
  addImage(img) { const i = new WImage(img); this.items.push(i); return i; }
  layoutHorizontally() { this.dir = "h"; } layoutVertically() { this.dir = "v"; } centerAlignContent() {} setPadding() {}
}
const walk = (s, out = { t: [], i: [] }) => { for (const it of s?.items || []) { if (it instanceof WText) out.t.push(it); else if (it instanceof WImage) out.i.push(it); else if (it.items) walk(it, out); } return out; };

async function run(o) {
  const env = { req: [], files: o.files || {}, kc: { [KEY]: TOKEN }, widget: null, imgReq: 0 };
  class Color { constructor(h) { this.hex = h; } static dynamic(l, d) { const c = new Color(l.hex); c.dark = d.hex; return c; } }
  const mk = w => s => ({ size: s, w });
  class ListWidget extends WStack { async presentSmall() { env.widget = this; } async presentMedium() { env.widget = this; } async presentLarge() { env.widget = this; } }
  class Request {
    constructor(url) { this.url = url; this.headers = {}; }
    async loadJSON() { env.req.push(this); const r = o.server(this); this.response = { statusCode: r.status }; if (r.throw) throw new Error(r.throw); return r.body; }
    async loadImage() { env.imgReq += 1; if (o.badLogo && this.url.includes(o.badLogo)) throw new Error("404"); return { img: this.url }; }
  }
  const FileManager = { local: () => ({
    documentsDirectory: () => "/docs", joinPath: (a, b) => a + "/" + b, fileExists: p => p in env.files || (p.endsWith("_logos") && env.dir),
    createDirectory: () => { env.dir = true; }, readString: p => env.files[p], writeString: (p, s) => { env.files[p] = s; },
    writeImage: (p, i) => { env.files[p] = i; }, readImage: p => env.files[p], modificationDate: () => new Date() }) };
  const ctx = vm.createContext({
    Color, Font: { systemFont: mk("r"), boldSystemFont: mk("b"), semiboldSystemFont: mk("sb") }, ListWidget, Size: class { constructor(w, h) { this.w = w; this.h = h; } },
    DateFormatter: class { string(d) { return new Date(d).toISOString().slice(11, 16); } }, Request, FileManager,
    Keychain: { contains: k => k in env.kc, get: k => env.kc[k], set: (k, v) => { env.kc[k] = v; } }, Alert: class {},
    config: { runsInWidget: true, widgetFamily: o.family }, args: { widgetParameter: o.param },
    Script: { setWidget: w => { env.widget = w; }, complete: () => {} }, console: { log: () => {} }, Promise,
  });
  try { await vm.runInContext("(async () => {\n" + script + "\n})()", ctx, { timeout: 5000 }); } catch (e) { env.err = String(e).split("\n")[0]; }
  return env;
}
const ITEMS = [["^TASI.SR", "تاسي", 9957.68, 20.42], ["1120", "الراجحي", 60.95, -0.2], ["2020", "سابك للمغذيات", 112.9, -0.4], ["2222", "أرامكو", 26.28, 0.14],
  ["7010", "اس تي سي", 40.38, 0.28], ["1150", "الإنماء", 21.25, 0.1], ["4190", "جرير", null, null], ["4030", "البحري", 34.6, -0.1],
  ["2286", "المطاحن", 3.86, 0.02], ["4001", "أسواق العثيم", 3.57, -0.03], ["1322", "معادن", 59.05, 0.75], ["4013", "الحبيب", 204, -3],
  ["7202", "سلوشنز", 84.35, -0.7], ["4164", "النهدي", 89.4, -1.95], ["4340", "الراجحي ريت", 7.81, 0.03], ["2270", "سدافكو", 184, 1.3], ["2050", "صافولا", 25, 0.1]]
  .map(([symbol, name, price, change]) => ({ symbol, name, price, change, change_pct: null, logo: "/market/logo/" + (/^\d{4}$/.test(symbol) ? symbol + ".SR" : symbol) }));
const DATA = { at: "2026-11-24T09:26:00+00:00", list: "السوق السعودي", lists: [], items: ITEMS };
const ok = d => () => ({ status: 200, body: { success: true, data: d } });

// ١ الطلب
const a = await run({ family: "large", param: "list:السوق السعودي", server: ok(DATA) });
const b = await run({ family: "medium", param: "list", server: ok({ ...DATA, list: "محفظتي" }) });
say(!a.err && a.req[0]?.url === `${ORIGIN}/api/v1/widget/watchlist?list=${encodeURIComponent("السوق السعودي")}` && a.req[0]?.headers?.["X-Widget-Token"] === TOKEN
    && b.req[0]?.url === `${ORIGIN}/api/v1/widget/watchlist` && !a.req[0].url.includes(TOKEN),
    "١ ‏list ⇒ القائمةُ الافتراضية، و‏list:اسم ⇒ القائمةُ باسمها — والرمزُ في الترويسة لا الرابط", a.err || a.req[0]?.url);

// ٢ عمودان من اليمين
const rows = (a.widget?.items || []).filter(x => x instanceof WStack && x.dir === "h" && x.items.filter(y => y instanceof WStack).length === 2);
const symOf = cell => walk(cell).t.find(t => t.font?.w === "b" && t.font?.size === 13)?.text;
const pairs = rows.map(r => r.items.filter(y => y instanceof WStack).map(symOf));
const all = walk(a.widget);
say(pairs.length === 8 && pairs[0][1] === "TASI" && pairs[0][0] === "1120" && pairs[1][1] === "2020" && pairs[1][0] === "2222"
    && all.t.some(t => t.text === "+1") && all.t.some(t => t.text === "السوق السعودي"),
    "٢ الكبير: ثمانيةُ صفوفٍ في عمودين، الأوّلُ يمينٌ والثاني يساره (تاسي يميناً والراجحي يساره)، وما زاد «+1»", JSON.stringify(pairs.slice(0, 2)));
const medRows = (b.widget?.items || []).filter(x => x instanceof WStack && x.dir === "h" && x.items.filter(y => y instanceof WStack).length === 2);
const s1 = await run({ family: "small", param: "list", server: ok(DATA) });
const smallSyms = walk(s1.widget).t.filter(t => t.font?.w === "b" && t.font?.size === 13).map(t => t.text);
say(medRows.length === 3 && smallSyms.length === 3 && smallSyms[0] === "TASI",
    "٢ب المتوسّط ستّةٌ في ثلاثة صفوف، والصغيرُ ثلاثةٌ في عمودٍ واحد", `${medRows.length} · ${smallSyms.join(",")}`);
const cellTexts = walk(pairs.length ? rows[0].items.filter(y => y instanceof WStack)[1] : null).t.map(t => t.text);
say(cellTexts.includes("TASI") && cellTexts.includes("تاسي") && cellTexts.includes("9,957.68") && cellTexts.includes("+20.42")
    && walk(rows[0]).i.length === 2 && walk(rows[0]).t.find(t => t.text === "−0.20")?.textColor?.hex === "#b91c1c",
    "٢ج لكلّ شركةٍ شعارُها ورمزُها واسمُها وسعرُها وتغيّرُها بلونه (الهبوطُ أحمر)", cellTexts.join(" | "));

// ٣ الشعار
const logoReq1 = a.imgReq;
const a2 = await run({ family: "large", param: "list:السوق السعودي", server: ok(DATA), files: a.files });
const c = await run({ family: "medium", param: "list", server: ok({ ...DATA, items: ITEMS.slice(0, 2) }), badLogo: "1120" });
const fallback = walk(c.widget).t.find(t => t.text === "1" && t.font?.w === "b" && t.font?.size === 11);
say(logoReq1 === 16 && a2.imgReq === 0 && walk(c.widget).i.length === 1 && !!fallback && a.files && Object.keys(a.files).some(k => k.includes("smart_portfolio_logos/1120.SR.png")),
    "٣ الشعارُ من بابنا ويُحفظ في الجهاز (التحديثُ التالي بلا جلب)، وما تعذّر شعارُه دائرةٌ بحرفه", `${logoReq1} · ${a2.imgReq} · ${walk(c.widget).i.length}`);

// ٤ الصدق والقراءة
const na = all.t.filter(t => t.text === "غير متوفّر");
const indic = all.t.filter(t => /[٠-٩]/.test(t.text));
const minF = Math.min(...all.t.map(t => t.font?.size ?? 99));
const miss = await run({ family: "medium", param: "list:لا شيء", server: () => ({ status: 404, body: { detail: "لا قائمةَ بهذا الاسم" } }) });
const lock = await run({ family: "accessoryRectangular", param: "list", server: ok(DATA) });
say(na.length >= 1 && !all.t.some(t => /^0(\.0+)?$/.test(t.text)) && indic.length === 0 && minF >= 9.5
    && walk(miss.widget).t.some(t => t.text === "القائمةُ غيرُ موجودة") && walk(lock.widget).t.length === 3 && walk(lock.widget).t[0].text.startsWith("TASI"),
    "٤ ما لا سعرَ له «غير متوفّر»، والأرقامُ لاتينية، والخطُّ ≥ 9.5، وقائمةٌ غائبة «القائمةُ غيرُ موجودة»، وشاشةُ القفل ثلاثةُ أسطر",
    `${na.length} · ${minF} · ${walk(lock.widget).t.map(t => t.text).join(" | ")}`);

console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
