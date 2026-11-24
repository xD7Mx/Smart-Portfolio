/* ‏D791 — سكربتُ ويدجت الآيفون (تطبيقُ «Scriptable» المجانيّ).

   ويدجت الآيفون الأصيلُ لا يصنعه إلا تطبيقٌ أصيلٌ يُبنى بـXcode على ماك — و«Scriptable» يرسم ويدجت الشاشة الرئيسية من سكربتٍ
   يقرأ نقطةَ الملخّص في خادمنا (‏/widget/summary) برمز الويدجت. يُبنى السكربتُ هنا بعنوان التطبيق الذي فُتح منه؛ والرمزُ **لا** يُكتب
   فيه أبداً: يُطلب عند أوّل تشغيلٍ ويُحفظ في سلسلة مفاتيح الآيفون (‏Keychain).

   الألوانُ قيمُ رموز التطبيق في ‏globals.css (المظهران بـ‏Color.dynamic):
     --bg · --ink · --ink-muted · --brand-ink · --hairline؛ والربحُ والخسارة: في الداكن ‏--pos-ink · --neg-ink، وفي الفاتح ‏--st-open · --st-closed
     (‏#15803d · #b91c1c — 5.02:1 و6.47:1 على الأبيض؛ ‏--pos-ink الفاتح #16a34a دون 4.5:1 لنصٍّ صغير). وأصغرُ خطٍّ 10 (≥ 9.5).
   والأرقامُ لاتينية، والنصُّ عربيّ، والمحاذاةُ يمين. */

const SCRIPT = String.raw`// المحفظة الذكية — ويدجت الشاشة الرئيسية (Scriptable)
// يقرأ ملخّصَ محفظتك من خادم التطبيق برمز الويدجت (من الإعدادات ← ويدجت الآيفون).
// الرمزُ يُحفظ في سلسلة مفاتيح الآيفون — لا في هذا السكربت.
// معامل الويدجت (Parameter): فارغ = المحفظة الافتراضية · all = كل المحافظ · رقم = محفظة بعينها.
// يعمل على الشاشة الرئيسية (صغير · متوسط · كبير) وعلى شاشة القفل.

const ORIGIN = __ORIGIN__;
const API = __API__;
const KEY = "smart_portfolio_widget_token";
const CACHE = "smart_portfolio_widget.json";

const C = (light, dark) => Color.dynamic(new Color(light), new Color(dark));
const COL = {
  bg: C("#ffffff", "#0d0d0d"), ink: C("#111111", "#ffffff"), muted: C("#4a4a4a", "#b3b3b3"),
  brand: C("#4f46e5", "#a5b4fc"), line: C("#e6e6e6", "#242424"),
  pos: C("#15803d", "#34d399"), neg: C("#b91c1c", "#f87171"),
};

const NA = "غير متوفّر";
const n0 = v => v == null ? NA : Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
const sg = v => v == null ? "" : (v > 0 ? "+" : v < 0 ? "−" : "");
const abs0 = v => v == null ? NA : Math.abs(Number(v)).toLocaleString("en-US", { maximumFractionDigits: 0 });
const pct = v => v == null ? NA : sg(v) + Math.abs(Number(v)).toFixed(2) + "%";
const tone = v => v == null ? COL.muted : v > 0 ? COL.pos : v < 0 ? COL.neg : COL.muted;
const hhmm = iso => { try { const d = new DateFormatter(); d.locale = "en"; d.dateFormat = "HH:mm"; return d.string(new Date(iso)); } catch (e) { return ""; } };

async function token(ask) {
  if (!ask && Keychain.contains(KEY)) return Keychain.get(KEY);
  if (config.runsInWidget) return null;
  const a = new Alert();
  a.title = "رمز الويدجت";
  a.message = "من التطبيق: الإعدادات ← ويدجت الآيفون ← «إنشاء رمز»، ثمّ الصقه هنا.";
  a.addSecureTextField("spw_…", "");
  a.addAction("حفظ");
  a.addCancelAction("إلغاء");
  if ((await a.present()) === -1) return null;
  const t = (a.textFieldValue(0) || "").trim();
  if (t) Keychain.set(KEY, t);
  return t || null;
}

function cachePath() { const fm = FileManager.local(); return fm.joinPath(fm.documentsDirectory(), CACHE); }
function saveCache(d) { try { FileManager.local().writeString(cachePath(), JSON.stringify(d)); } catch (e) {} }
function readCache() { try { const fm = FileManager.local(); return fm.fileExists(cachePath()) ? JSON.parse(fm.readString(cachePath())) : null; } catch (e) { return null; } }

async function load(t, pf) {
  const r = new Request(API + "/widget/summary" + (pf ? "?pf=" + encodeURIComponent(pf) : ""));
  r.headers = { "X-Widget-Token": t };
  r.timeoutInterval = 20;
  let j = null;
  try { j = await r.loadJSON(); } catch (e) { j = null; }
  const code = r.response ? r.response.statusCode : 0;   // ‏401 يُعرف من الحالة وإن لم يكن الجسمُ JSON
  if (code === 401) return { error: "auth" };
  if (!j || !j.success || !j.data) return { error: "net" };
  return { data: j.data };
}

function txt(parent, s, size, color, bold) {
  const t = parent.addText(String(s));
  t.font = bold ? Font.boldSystemFont(size) : Font.systemFont(size);
  t.textColor = color;
  t.rightAlignText();
  t.lineLimit = 1;
  t.minimumScaleFactor = 0.6;
  return t;
}

function row(parent, label, value, color, size) {
  const s = parent.addStack();
  s.layoutHorizontally();
  s.centerAlignContent();
  const v = s.addText(String(value)); v.font = Font.semiboldSystemFont(size || 12); v.textColor = color || COL.ink; v.lineLimit = 1; v.minimumScaleFactor = 0.6;
  s.addSpacer();
  const l = s.addText(String(label)); l.font = Font.systemFont((size || 12) - 1); l.textColor = COL.muted; l.lineLimit = 1;
  return s;
}

function header(w, d, stale) {
  const s = w.addStack();
  s.layoutHorizontally();
  const tm = s.addText((stale ? "آخر تحديث " : "") + hhmm(d.at)); tm.font = Font.systemFont(10); tm.textColor = COL.muted;
  s.addSpacer();
  const t = s.addText(d.portfolio || "المحفظة الذكية"); t.font = Font.boldSystemFont(11); t.textColor = COL.brand; t.lineLimit = 1;
}

function build(d, stale, family) {
  const w = new ListWidget();
  w.backgroundColor = COL.bg;
  w.setPadding(12, 14, 12, 14);
  w.url = ORIGIN + "/portfolio";
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  header(w, d, stale);
  w.addSpacer(6);
  txt(w, "إجمالي الثروة", 10, COL.muted, false);
  txt(w, n0(d.wealth), family === "small" ? 22 : 26, COL.ink, true);
  const day = d.day_change == null ? NA : sg(d.day_change) + abs0(d.day_change) + "  (" + pct(d.day_change_pct) + ") اليوم";
  txt(w, day, 11, tone(d.day_change), true);
  w.addSpacer(family === "small" ? 6 : 8);
  if (family === "small") {
    row(w, "صافي الربح", d.net_profit == null ? NA : sg(d.net_profit) + abs0(d.net_profit), tone(d.net_profit), 11);
    row(w, "عائد المحفظة", pct(d.return_pct), tone(d.return_pct), 11);
    w.addSpacer();
    return w;
  }
  row(w, "صافي الربح", d.net_profit == null ? NA : sg(d.net_profit) + abs0(d.net_profit), tone(d.net_profit));
  row(w, "عائد المحفظة", pct(d.return_pct), tone(d.return_pct));
  row(w, "تاسي", d.tasi ? Number(d.tasi.price).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "  " + pct(d.tasi.change_pct) : NA, d.tasi ? tone(d.tasi.change_pct) : COL.muted);
  if (family === "large" || family === "extraLarge") {
    w.addSpacer(10);
    const sep = w.addStack(); sep.size = new Size(0, 1); sep.backgroundColor = COL.line;
    w.addSpacer(8);
    txt(w, "الحيازات", 10, COL.muted, false);
    w.addSpacer(4);
    for (const h of (d.holdings || []).slice(0, 6)) {
      row(w, (h.name || h.symbol || "") + "  " + (h.symbol || ""), pct(h.change_pct) + "   " + n0(h.value), tone(h.change_pct), 12);
      w.addSpacer(3);
    }
  }
  w.addSpacer();
  return w;
}

function message(title, body) {
  const w = new ListWidget();
  w.backgroundColor = COL.bg;
  w.setPadding(14, 14, 14, 14);
  w.url = ORIGIN + "/settings";
  txt(w, "المحفظة الذكية", 11, COL.brand, true);
  w.addSpacer(6);
  txt(w, title, 13, COL.ink, true);
  const b = w.addText(body); b.font = Font.systemFont(11); b.textColor = COL.muted; b.rightAlignText();
  return w;
}

// شاشةُ القفل (‏accessory*): مساحةٌ صغيرة يلوّنها النظام — الثروةُ وتغيّرُ اليوم وحدهما
function accessory(d, stale, family) {
  const w = new ListWidget();
  w.url = ORIGIN + "/portfolio";
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  const dp = pct(d.day_change_pct);
  if (family === "accessoryInline") {
    txt(w, stale ? "آخر تحديث " + hhmm(d.at) + " · " + n0(d.wealth) : "الثروة " + n0(d.wealth) + " · " + dp + " اليوم", 12, COL.ink, false);
    return w;
  }
  if (family === "accessoryCircular") {
    txt(w, "اليوم", 10, COL.muted, false);
    txt(w, dp, 12, tone(d.day_change_pct), true);
    return w;
  }
  txt(w, stale ? "آخر تحديث " + hhmm(d.at) : (d.portfolio || "المحفظة الذكية"), 10, COL.muted, true);
  txt(w, n0(d.wealth), 17, COL.ink, true);
  txt(w, d.day_change == null ? NA : sg(d.day_change) + abs0(d.day_change) + " (" + dp + ") اليوم", 11, tone(d.day_change), false);
  return w;
}

function accessoryMsg(s) {
  const w = new ListWidget();
  w.url = ORIGIN + "/settings";
  txt(w, "المحفظة الذكية", 10, COL.muted, true);
  txt(w, s, 11, COL.ink, false);
  return w;
}

async function main() {
  const family = config.widgetFamily || "medium";
  const acc = String(family).indexOf("accessory") === 0;     // شاشةُ القفل
  const pf = (args.widgetParameter || "").trim();
  let t = await token(false);
  if (!t) { Script.setWidget(acc ? accessoryMsg("أدخل الرمز في Scriptable") : message("رمزُ الويدجت غيرُ مُدخَل", "افتح Scriptable وشغّل السكربت مرّةً والصق الرمز.")); Script.complete(); return; }
  let r = await load(t, pf);
  if (r.error === "auth" && !config.runsInWidget) { t = await token(true); if (t) r = await load(t, pf); }
  let w;
  if (r.data) { saveCache(r.data); w = acc ? accessory(r.data, false, family) : build(r.data, false, family); }
  else if (r.error === "auth") w = acc ? accessoryMsg("الرمزُ غيرُ صالح") : message("الرمزُ غيرُ صالح", "أنشئ رمزاً جديداً من الإعدادات في التطبيق ثمّ شغّل السكربت مرّةً والصقه.");
  else {
    const c = readCache();
    w = c ? (acc ? accessory(c, true, family) : build(c, true, family))
          : (acc ? accessoryMsg("تعذّر التحديث") : message("تعذّر التحديث", "لا اتصال بالخادم الآن — سيُعاد المحاولة تلقائياً."));
  }
  if (config.runsInWidget) Script.setWidget(w);
  else if (family === "small") await w.presentSmall();
  else if (family === "large") await w.presentLarge();
  else await w.presentMedium();
  Script.complete();
}

await main();
`;

/** السكربتُ بعنوان التطبيق الذي فُتح منه — بلا رمزٍ فيه. */
export function widgetScript(origin: string, apiBase: string): string {
  const api = /^https?:/i.test(apiBase) ? apiBase : origin.replace(/\/$/, "") + (apiBase.startsWith("/") ? apiBase : "/" + apiBase);
  return SCRIPT.replace("__ORIGIN__", JSON.stringify(origin.replace(/\/$/, ""))).replace("__API__", JSON.stringify(api.replace(/\/$/, "")));
}
