// ─────────────────────────────────────────────────────────────────────────
// D333 — قسمُ التقارير: يُفتح في متصفّحٍ ببياناتٍ ناقصةٍ عن قصد.
//
// قال المالك: «قسمُ التقارير به أخطاءٌ اكتشفها جميعَها ثمّ أصلحها». والذي
// وُجد بالقراءة ثمّ قِيس هنا:
//   · حبرُ الورقة كان بألوان **مظهر التطبيق** (`var(--ink)`) وأرضيتُها
//     ثابتةٌ — فحبرٌ أسودُ على ترويسةٍ بنفسجيةٍ في المظهر الفاتح.
//   · و«الأرباح غير المحققة» و«نسبتُها» كانتا تُصفَّران عند الغياب،
//     وجارتاهما في الشبكة نفسِها تعرضان «—».
//   · وتاريخُ الإصدار الغائبُ كان يُملأ بتاريخ **اليوم**.
//   · ونسبةُ ربحِ المركز الغائبةُ كانت «(0.0%)».
//   · ونوعُ التقرير كان يُعرض `WEEKLY` في شاشةٍ عربية.
//   · وتاريخُ القائمة `en-GB` والورقةُ عربيةٌ — صيغتان لقيمةٍ واحدة.
//   · وشريطٌ بنفسجيٌّ بارتفاع ٥٠px **فارغٌ** يُذيّل الورقة.
//
// فيُخدَم تقريرٌ حقوله ناقصةٌ قصداً، ويُقرأ **نصُّ الورقة كما رُسم**.
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

// ── تقريرٌ حقولُه ناقصةٌ قصداً ───────────────────────────────────────────
const REPORT = {
  id: 1, type: "WEEKLY", period: "أسبوعي · ينتهي 2026-09-10",
  generated_at: null,                 // بلا تاريخِ إصدار
  overall_score: null,
  content: null,
  metrics: {
    market_value: 84646.05, total_invested: 77183.15,
    unrealized_pnl: null,             // غائبٌ — لا صفر
    roi_pct: null,                    // غائبٌ — لا صفر
    wealth: 90000, net_profit: null,
    capital_growth_pct: null, cagr_pct: null, cash_pct: 5.9,
    positions_count: 1,
  },
  positions: [{ name: "مصرف الراجحي", symbol: "1120", shares: 290,
                market_value: 19111, pnl: 1234, pnl_pct: null }],
};
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript",
               ".css": "text/css", ".json": "application/json",
               ".woff2": "font/woff2", ".svg": "image/svg+xml",
               ".png": "image/png", ".webmanifest": "application/manifest+json" };
const env = (data) => JSON.stringify({ success: true, data });

const srv = createServer((req, res) => {
  const p = new URL(req.url, "http://x").pathname;
  if (p.startsWith("/api/v1/")) {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    if (p === "/api/v1/reports") {
      return res.end(env([{ id: 1, type: "WEEKLY",
                            period: REPORT.period,
                            generated_at: "2026-09-16T08:30:00+00:00",
                            has_content: true }]));
    }
    if (p === "/api/v1/reports/1") return res.end(env(REPORT));
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
// المظهرُ الفاتحُ قصداً: فيه كان حبرُ الترويسة يسقط إلى السواد.
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 },
                                       colorScheme: "light" });
await ctx.addInitScript(() => {
  try {
    localStorage.setItem("sp_token", "probe");
    localStorage.setItem("theme", "light");
  } catch { /* خاصّ */ }
});
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 140)));

await page.goto(`http://127.0.0.1:${PORT}/reports`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1800);

// ── ٠ · الأرشيفُ يُرسم، والنوعُ بالعربية ────────────────────────────────
const list = await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("أرشيف التقارير"));
  const card = h?.closest(".card");
  return (card?.textContent || "").replace(/\s+/g, " ").trim();
});
say(list.includes("أسبوعي"),
    "٠ نوعُ التقرير بالعربية في الأرشيف — لا `WEEKLY` في شاشةٍ عربية",
    list.slice(0, 90));
say(!/WEEKLY|MONTHLY|QUARTERLY|ANNUAL|DAILY/.test(list),
    "٠ب ولا لفظٌ إنجليزيٌّ باقٍ في الأرشيف",
    (list.match(/WEEKLY|MONTHLY|QUARTERLY|ANNUAL|DAILY/) || [""])[0] || "نظيف");
say(!/\d{2}\/\d{2}\/\d{4}/.test(list),
    "٠ج وتاريخُ الأرشيف بصيغة التطبيق لا `en-GB`",
    (list.match(/\d{2}\/\d{2}\/\d{4}/) || [""])[0] || "نظيف");

// ── ١ · تُفتح الورقةُ ويُقرأ نصُّها ─────────────────────────────────────
const opened = await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")]
    .find(x => (x.textContent || "").includes("عرض"));
  if (!b) return false;
  b.click();
  return true;
});
await page.waitForTimeout(1500);
const doc = await page.evaluate(() => {
  const el = document.querySelector(".report-doc");
  if (!el) return null;
  const grab = (txt) => {
    const box = [...el.querySelectorAll("div")]
      .find(d => d.children.length === 0 && (d.textContent || "").trim() === txt);
    return box?.parentElement?.lastElementChild?.textContent?.trim() || null;
  };
  // ══ يُقرأ العنصرُ **الذي يرسم النصّ** لا جدُّه ══
  // أوّلُ صياغةٍ أخذت أوّلَ `div` يحتوي العبارة — وهو الأبُ الذي يورَث
  // حبرُه من الورقة، فقِيس سوادُ الورق لا حبرُ الترويسة. فيُنتقى أعمقُ
  // عنصرٍ لا أبناءَ له.
  const head = [...el.querySelectorAll("div")]
    .filter(d => d.children.length === 0
                 && (d.textContent || "").includes("تاريخ الإصدار"))
    .pop();
  const cs = head ? getComputedStyle(head).color : null;
  return {
    text: (el.textContent || "").replace(/\s+/g, " ").trim(),
    upnl: grab("الأرباح غير المحققة"),
    roi: grab("نسبة الأرباح غير المحققة"),
    headColor: cs,
    footer: (() => {
      const last = el.lastElementChild;
      return last ? { h: Math.round(last.getBoundingClientRect().height),
                      txt: (last.textContent || "").trim() } : null;
    })(),
  };
});
say(opened && doc,
    "١ ورقةُ التقرير تُفتح وتُرسم", doc ? `${doc.text.length} حرفاً` : "لا ورقة");

// ── ٢ · الغائبُ شرطةٌ لا صفر ───────────────────────────────────────────
say(doc?.upnl === "—" && doc?.roi === "—",
    "٢ الغائبُ في الشبكة شرطةٌ لا «+0» ولا «+0.00%»",
    `أرباحٌ=${doc?.upnl} · نسبةٌ=${doc?.roi}`);
say(!!doc && /تاريخ الإصدار: —/.test(doc.text),
    "٢ب وتاريخُ إصدارٍ غائبٌ يُقال شرطةً — لا يُملأ بتاريخ اليوم",
    (doc?.text.match(/تاريخ الإصدار: [^ ]+/) || [""])[0]);
say(!!doc && !/\(0\.0%\)/.test(doc.text),
    "٢ج ونسبةُ ربحِ مركزٍ غائبةٌ لا تُعرض «(0.0%)»",
    /\(0\.0%\)/.test(doc?.text || "") ? "وُجدت" : "نظيف");

// ── ٣ · وحبرُ الورقة من لوحها لا من مظهر التطبيق ───────────────────────
// في المظهر الفاتح كان `var(--ink)` حبراً شبهَ أسودَ على ترويسةٍ بنفسجية.
const light = (() => {
  const m = /rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(doc?.headColor || "");
  if (!m) return null;
  const [r, g, b] = [+m[1], +m[2], +m[3]];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;   // سطوعٌ تقريبيّ
})();
say(light != null && light > 140,
    "٣ حبرُ ترويسة الورقة فاتحٌ على أرضيتها البنفسجية — في المظهر الفاتح",
    `${doc?.headColor} · سطوع ${light == null ? "—" : Math.round(light)}`);

// ── ٤ · ولا شريطٌ ملوّنٌ فارغٌ يُذيّل الورقة ────────────────────────────
say(doc?.footer && (doc.footer.txt.length > 0 || doc.footer.h <= 10),
    "٤ ذيلُ الورقة شريطُ هويّةٍ رقيقٌ لا صندوقٌ خاوٍ بارتفاعٍ كبير",
    `ارتفاع ${doc?.footer?.h}px · نصٌّ «${doc?.footer?.txt}»`);

for (const e of errs) console.log(`     خطأٌ في الصفحة: ${e}`);
say(errs.length === 0, "٥ ولا خطأَ في الصفحة", errs.slice(0, 2).join(" · "));

await browser.close();
srv.close();
console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
