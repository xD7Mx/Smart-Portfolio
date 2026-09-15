// ─────────────────────────────────────────────────────────────────────────
// D301 — «هل أنت متأكّد؟»: الرقمُ يتحرّك على شاشةٍ حقيقيةٍ أو لا يتحرّك.
//
// سأل المالك: «هل أنت متأكّد؟ توعدني كثيراً والنتيجةُ سيّئة». وكان حقّاً:
// كلُّ ما أثبتُّه عن الفورية كان **شيفرةً وحرّاساً**، ولم أفتح التطبيقَ في
// متصفّحٍ قطّ لأرى رقماً يتغيّر. والوعدُ الذي لا يُقاس ليس إثباتاً.
//
// فهذا الفحصُ يقيس ما يراه هو بعينه:
//   · يُخدَم **بناءُ الواجهة الحقيقيُّ** (‏build) من خادمٍ محليٍّ واحد
//   · وإلى جانبه مجرى أحداثٍ حقيقيٌّ يدفع سعراً متغيّراً ومؤشّراً متغيّراً
//   · ويُفتح `/market` في كروميوم، ويُلتقَط نصُّ الرقم كلَّ مئة مل.ث
//   · فيُحسَب: كم مرّةً تغيّر الرقمُ فعلاً، وكم أطولُ فجوةٍ بين تغيّرين
//
// والحكمُ بالأرقام: تغيّرٌ لا يقلّ عن أربع مرّاتٍ في ثلاث ثوان، وفجوةٌ لا
// تتجاوز ثانيةً واحدة. وإن غاب المتصفّحُ قال ذلك ولم يحكم.
// ─────────────────────────────────────────────────────────────────────────
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const BUILD = join(ROOT, "frontend", "build");
// ══ منفذٌ يُعطاه النظام ══
// أوّلُ صياغةٍ ثبّتت المنفذ، فسقط الفحصُ في بناء الحزمة بـ`EADDRINUSE`
// لأن تشغيلاً سابقاً ما زال يحتلّه — وحارسٌ نتيجتُه تتبع ما حول البيئة
// ليس حارساً (الدرسُ نفسُه الذي تعلّمتُه من الطورِ المقروء من الساعة).
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

// ── خادمٌ واحد: الواجهةُ الحقيقيةُ ومجرًى حقيقيٌّ بجانبها ───────────────
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript",
               ".css": "text/css", ".json": "application/json",
               ".woff2": "font/woff2", ".svg": "image/svg+xml",
               ".png": "image/png", ".webmanifest": "application/manifest+json" };
let price = 70.00;
let tasi = 11500.0;
const env = (data) => JSON.stringify({ success: true, data });

const srv = createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  const p = url.pathname;

  // مجرى الأحداث: يدفع سعراً ومؤشّراً كلَّ 300 مل.ث — كما تدفع المضخّة.
  if (p === "/api/v1/market/stream") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
    });
    res.write(": open\n\n");
    const t = setInterval(() => {
      price = Math.round((price + 0.05) * 100) / 100;
      tasi = Math.round((tasi + 1.3) * 10) / 10;
      res.write("data: " + JSON.stringify({
        t: new Date().toTimeString().slice(0, 8),
        q: { "2010": [price, 0.42] }, i: [tasi, 0.31],
        live: true, at: new Date().toISOString(),
      }) + "\n\n");
    }, 300);
    req.on("close", () => clearInterval(t));
    return;
  }

  if (p.startsWith("/api/v1/")) {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    if (p === "/api/v1/settings/server-time") {
      return res.end(env({ market_status: "open", time: "13:00",
                           date: new Date().toISOString().slice(0, 10) }));
    }
    if (p === "/api/v1/market/overview") {
      return res.end(env({ tasi: { symbol: "^TASI", price: tasi,
                                   change_pct: 0.31, prev_close: 11460 },
                           brent: null }));
    }
    if (p === "/api/v1/market/movers") {
      return res.end(env({
        advancers: 120, decliners: 80, total: 200, sectors: [],
        gainers: [{ symbol: "2010", name: "سابك", price, change_pct: 0.42 }],
        losers: [{ symbol: "1120", name: "الراجحي", price: 65.9, change_pct: -0.3 }],
      }));
    }
    if (p === "/api/v1/market/summary") {
      return res.end(env({ phase: "open", text: "" }));
    }
    return res.end(env([]));
  }

  // ملفّاتُ البناء، وكلُّ مسارٍ غيرِها يعود إلى index.html (تطبيقُ صفحةٍ واحدة)
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

await page.goto(`http://127.0.0.1:${PORT}/market`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(2500);

/** يُلتقَط نصُّ أوّلِ عنصرٍ يطابق المحدّد، عشراتِ المرّات، ويُحسَب تغيّرُه. */
async function watch(sel, label, seconds = 3) {
  const seen = [];
  const at = [];
  const t0 = Date.now();
  while (Date.now() - t0 < seconds * 1000) {
    const txt = await page.evaluate((s) => {
      const el = document.querySelector(s);
      return el ? (el.textContent || "").replace(/\s+/g, " ").trim() : null;
    }, sel);
    if (txt != null && (seen.length === 0 || seen[seen.length - 1] !== txt)) {
      seen.push(txt);
      at.push(Date.now() - t0);
    }
    await page.waitForTimeout(100);
  }
  const changes = Math.max(0, seen.length - 1);
  let gap = 0;
  for (let i = 1; i < at.length; i++) gap = Math.max(gap, at[i] - at[i - 1]);
  console.log(`     ${label}: ${seen.slice(0, 4).join(" → ")}${seen.length > 4 ? " …" : ""}`);
  return { changes, gap, first: seen[0] ?? null };
}

const tick = await watch(".mk-item", "شريطُ السوق");
say(tick.changes >= 4 && tick.gap <= 1000,
    "٠ رقمُ الشريط يتغيّر على الشاشة فعلاً",
    `${tick.changes} تغيّراً في 3 ثوانٍ · أطولُ فجوة ${tick.gap} مل.ث`);

const idx = await watch(".mk-tasi", "لسانُ تاسي");
say(idx.changes >= 4 && idx.gap <= 1000,
    "١ ومؤشّرُ تاسي كذلك — لا رقمٌ يُسأل عنه كلَّ دقيقة",
    `${idx.changes} تغيّراً · أطولُ فجوة ${idx.gap} مل.ث`);

// وبطاقةُ نبض السوق: الرقمُ الكبيرُ نفسُه الذي قال المالكُ إنه ثابت.
const pulse = await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("نبض السوق"));
  const card = h?.closest(".card");
  const el = card?.querySelector('[dir="ltr"], .tabular-nums');
  return el ? (el.textContent || "").trim() : null;
});
say(pulse != null && /\d/.test(pulse),
    "٢ وبطاقةُ «نبض السوق» تعرض رقمَ المؤشّر لا شرطة", String(pulse).slice(0, 20));

// ══ ولا حالتان في بطاقةٍ واحدة ══ (بأمر المالك · D302)
// رأى المالكُ في «نبض السوق» وسماً يقول «جلسة مباشرة» ونقطةً تقول «السوق
// مغلق» — مصدرانِ لمعنًى واحدٍ يتناقضان. فالحالةُ لا تُعرض في هذه البطاقة
// أصلاً، ويُقاس ذلك من نصِّ البطاقة في المتصفّح لا من الشيفرة (فالتعليقُ
// الذي يشرح الحذفَ يحمل الكلماتَ نفسَها فيخدع فحصَ النصّ).
const cardTxt = await page.evaluate(() => {
  const h = [...document.querySelectorAll("h2")]
    .find(x => (x.textContent || "").includes("نبض السوق"));
  return (h?.closest(".card")?.textContent || "").replace(/\s+/g, " ");
});
const banned = ["جلسة مباشرة", "السوق مغلق", "بعد الإغلاق", "ما قبل الافتتاح"]
  .filter(w => cardTxt.includes(w));
say(banned.length === 0,
    "٤ ولا حالةَ سوقٍ في بطاقة «نبض السوق» — لا وسمانِ يتناقضان",
    banned.join(" · ") || "خالية");

for (const e of errs) console.log(`     خطأٌ في الصفحة: ${e}`);
say(errs.length === 0, "٣ ولا خطأَ في الصفحة أثناء الدفع");

await browser.close();
srv.close();
console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
