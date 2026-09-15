// ─────────────────────────────────────────────────────────────────────────
// D324 — تبويبُ الصفقات يُقاس في متصفّحٍ حقيقيّ: شعارٌ يُرسَم وبحثٌ يفرز.
//
// أمر المالكُ بحسنيَن في التبويب: **شعاراتُ الشركات**، و**أيقونةُ بحثٍ
// تتمدّد وتتلاشى** للبحث عن شركةٍ أو رمزٍ بعينه. وقبل يومٍ واحدٍ قال:
// «تبويب الصفقات الخاصة فاضي» — وكنتُ أقيس الدالّةَ ولا أفتح الشاشة
// (D322). فلا يُقال «تمّ» هنا إلا من **شاشةٍ تُفتح فعلاً**:
//
//   ٠· التبويبُ يُفتح ويُرسم بصفوفه
//   ١· ولكلّ صفٍّ شعارٌ مرسومٌ — صورةٌ أو بديلٌ بحرفه، لا فراغ
//   ٢· وأيقونةُ البحث مطويّةٌ أوّلاً، فتتمدّد بالضغط وحقلُها يظهر
//   ٣· وكتابةُ رمزٍ تفرز الصفوفَ فعلاً — لا زينةٌ لا تفعل
//   ٤· وكتابةُ الاسم الدارج تفرز كذلك (معادن ← التعدين العربية)
//   ٥· وكلمةٌ لا تطابق شيئاً تقول ذلك ولا تُخفي التبويب
//   ٦· والإغلاقُ يعيد الصفوفَ كلَّها
//   ٧· ولا خطأَ في الصفحة أثناء ذلك
//
// وإن غاب المتصفّحُ قال ذلك ولم يحكم — ولا يُعدّ غيابُه نجاحاً.
// ─────────────────────────────────────────────────────────────────────────
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const BUILD = join(ROOT, "frontend", "build");
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

if (!existsSync(join(BUILD, "index.html"))) {
  console.log("… تعذّر الفحص: لا بناءَ للواجهة (npm run build).");
  process.exit(0);
}
const PW = ["/opt/node22/lib/node_modules/playwright/index.js",
            "/usr/lib/node_modules/playwright/index.js",
            "/usr/local/lib/node_modules/playwright/index.js",
            join(ROOT, "frontend", "node_modules", "playwright", "index.js")]
  .find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) {
  console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح.");
  process.exit(0);
}
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
if (!chromium) {
  console.log("… تعذّر الفحص: لا `chromium` في حزمة playwright.");
  process.exit(0);
}

// ── صفقاتٌ بشكل المصدر كما وصل من «تداول» (‏getNegotiatedDetails) ────────
const DEALS = [
  { symbol: "2250", name: "المجموعة السعودية للأبحاث والإعلام",
    price: 11.62, quantity: 395000, value: 4589900,
    at: "15-09-2026", time: "14:13:11" },
  { symbol: "1211", name: "التعدين العربية السعودية",
    price: 58.4, quantity: 120000, value: 7008000,
    at: "14-09-2026", time: "11:02:40" },
  { symbol: "4200", name: "الدرع العربي",
    price: 121.3, quantity: 25000, value: 3032500,
    at: "12-09-2026", time: "11:59:22" },
];

const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript",
               ".css": "text/css", ".json": "application/json",
               ".woff2": "font/woff2", ".svg": "image/svg+xml",
               ".png": "image/png", ".webmanifest": "application/manifest+json" };
const env = (data) => JSON.stringify({ success: true, data });

const srv = createServer((req, res) => {
  const p = new URL(req.url, "http://x").pathname;
  if (p.startsWith("/api/v1/")) {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    if (p === "/api/v1/market/special-deals") {
      return res.end(env({ deals: DEALS, as_of: "2026-09-15T17:43:19+00:00",
                           available: true, count: DEALS.length, days: 30,
                           source: "تداول" }));
    }
    if (p === "/api/v1/settings/server-time") {
      return res.end(env({ market_status: "closed", time: "18:00",
                           date: new Date().toISOString().slice(0, 10) }));
    }
    return res.end(env([]));
  }
  let f = join(BUILD, p === "/" ? "index.html" : p.slice(1));
  if (!existsSync(f) || !statSync(f).isFile()) f = join(BUILD, "index.html");
  res.writeHead(200, { "Content-Type": MIME[extname(f)] || "application/octet-stream" });
  createReadStream(f).pipe(res);
});
await new Promise(r => srv.listen(0, "127.0.0.1", r));
const PORT = srv.address().port;

const browser = await chromium.launch({
  executablePath: CHROME, args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
await ctx.addInitScript(() => {
  try { localStorage.setItem("sp_token", "probe"); } catch { /* خاصّ */ }
});
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 120)));
// شعاراتُ المزوّد الخارجيّ لا تُطلَب من صندوقٍ بلا شبكة: تُردّ 404 فيسقط
// الشعارُ إلى بديله بحرفه — وهو ما يُقاس هنا (وجودُ شعارٍ لا مصدرُه).
await ctx.route("**://*/logos/**", r => r.fulfill({ status: 404, body: "" }));
await ctx.route("**://s3-symbol-logo.tradingview.com/**",
                r => r.fulfill({ status: 404, body: "" }));

await page.goto(`http://127.0.0.1:${PORT}/market`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1500);

// ── ٠ · التبويبُ يُفتح ويُرسم ───────────────────────────────────────────
const opened = await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")]
    .find(x => (x.textContent || "").trim() === "صفقات خاصة");
  if (!b) return false;
  b.click();
  return true;
});
await page.waitForTimeout(1200);

const rowsOf = () => page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("صفقات خاصة"));
  const card = h?.closest(".card");
  if (!card) return null;
  const rows = [...card.querySelectorAll("tbody tr")];
  return {
    rows: rows.length,
    logos: rows.filter(r => r.querySelector(".co-logo")).length,
    symbols: rows.map(r => (r.textContent || "").match(/\b\d{4}\b/)?.[0] || ""),
    text: (card.textContent || "").replace(/\s+/g, " ").trim().slice(0, 220),
    searchOpen: card.querySelector('.inline-search')?.dataset.open || null,
    inputSeen: (() => {
      const i = card.querySelector(".inline-search-input");
      if (!i) return null;
      const st = getComputedStyle(i);
      return { opacity: +st.opacity, width: i.getBoundingClientRect().width };
    })(),
  };
});

const s0 = await rowsOf();
say(opened && s0 && s0.rows === 3,
    "٠ التبويبُ يُفتح ويُرسم بصفوفه", `${s0?.rows ?? "لا بطاقة"} صفّاً`);

// ── ١ · شعارٌ لكلّ صفّ ──────────────────────────────────────────────────
say(!!s0 && s0.logos === s0.rows,
    "١ ولكلّ صفٍّ شعارٌ مرسوم — لا فراغَ مكانَ الهويّة",
    `${s0?.logos ?? 0}/${s0?.rows ?? 0}`);

// ── ٢ · الأيقونةُ مطويّةٌ ثمّ تتمدّد ────────────────────────────────────
say(s0?.searchOpen === "0" && (s0?.inputSeen?.opacity ?? 1) === 0,
    "٢ أيقونةُ البحث مطويّةٌ أوّلاً وحقلُها متلاشٍ",
    `مفتوح=${s0?.searchOpen} · شفافية=${s0?.inputSeen?.opacity}`);

const collapsedW = await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("صفقات خاصة"));
  const el = h?.closest(".card")?.querySelector(".inline-search");
  return el ? el.getBoundingClientRect().width : null;
});
await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("صفقات خاصة"));
  h?.closest(".card")?.querySelector(".inline-search-btn")?.click();
});
await page.waitForTimeout(500);
const s1 = await rowsOf();
const openW = await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("صفقات خاصة"));
  const el = h?.closest(".card")?.querySelector(".inline-search");
  return el ? el.getBoundingClientRect().width : null;
});
say(s1?.searchOpen === "1" && openW > (collapsedW || 0) + 60
    && (s1?.inputSeen?.opacity ?? 0) === 1,
    "٢ب فتتمدّد بالضغط ويظهر حقلُها — لا بطاقةٌ تُفتح فوقها",
    `${collapsedW}px ← ${openW}px · شفافية=${s1?.inputSeen?.opacity}`);

// ── ٣ · وكتابةُ رمزٍ تفرز فعلاً ─────────────────────────────────────────
const type = async (t) => {
  await page.evaluate(() => {
    const h = [...document.querySelectorAll("h2")]
      .find(x => (x.textContent || "").includes("صفقات خاصة"));
    h?.closest(".card")?.querySelector(".inline-search-input")?.focus();
  });
  await page.keyboard.press("Control+A").catch(() => {});
  if (t === "") { await page.keyboard.press("Backspace"); }
  else await page.keyboard.type(t, { delay: 15 });
  await page.waitForTimeout(400);
  return rowsOf();
};

const byCode = await type("4200");
say(byCode?.rows === 1 && byCode.symbols.includes("4200"),
    "٣ وكتابةُ رمزٍ تفرز الصفوفَ فعلاً", `${byCode?.rows} صفّاً · ${byCode?.symbols}`);

// ── ٤ · والاسمُ الدارجُ كذلك ────────────────────────────────────────────
const byAlias = await type("معادن");
say(byAlias?.rows === 1 && byAlias.symbols.includes("1211"),
    "٤ والاسمُ الدارجُ يفرز كما الرمز — معادن ← التعدين العربية",
    `${byAlias?.rows} صفّاً · ${byAlias?.symbols}`);

// ── ٥ · وما لا يطابق يُقال ولا يُخفى التبويب ───────────────────────────
const none = await type("زقزق");
say(none !== null && none.rows === 0 && /لا صفقة تطابق/.test(none.text),
    "٥ وكلمةٌ لا تطابق شيئاً تقول ذلك — لا بطاقةٌ خاوية",
    (none?.text || "").slice(0, 70));

// ── ٦ · والإغلاقُ يعيد الكلّ ────────────────────────────────────────────
await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("صفقات خاصة"));
  h?.closest(".card")?.querySelector(".inline-search-btn")?.click();
});
await page.waitForTimeout(500);
const s2 = await rowsOf();
say(s2?.rows === 3 && s2.searchOpen === "0",
    "٦ والإغلاقُ يطوي الحقلَ ويعيد الصفوفَ كلَّها",
    `${s2?.rows} صفّاً · مفتوح=${s2?.searchOpen}`);

say(errs.length === 0, "٧ ولا خطأَ في الصفحة أثناء ذلك", errs.slice(0, 2).join(" · "));

await browser.close();
srv.close();
console.log((fail ? "FAIL" : "PASS")
  + " D324 — شعارُ الصفّ مرسومٌ وبحثُ التبويب يفرز، مقيسَين في متصفّح");
process.exit(fail);
