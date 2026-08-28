/**
 * فحوص لجنة كشف الأعطال — الطبقة الحيّة (تفتح التطبيق وتقيس).
 *
 * الطبقة الساكنة تقرأ الشيفرة، وهذه تُشغّلها: كثيرٌ من الأعطاب لا يظهر إلا
 * بعد الرسم — نصٌّ يخرج عن الحافّة، شاشةٌ تُبنى فارغة، رقمٌ يُحسب `NaN`،
 * إعدادٌ يعمل على جهازٍ ويسقط على غيره.
 *
 * **وكلُّ فحصٍ يجري على متصفّحٍ نظيف** لا يحمل ذاكرةً محلّية: هذه هي
 * القاعدة التي كشفت عطب صفحة البداية، وهو عطبٌ عاش شهوراً لأنه كان يعمل
 * على جهاز المالك وحده.
 *
 *   تشغيل:  node scripts/audit/browser.mjs
 *   يحتاج:  SP_URL (افتراضياً http://127.0.0.1:8098) و SP_TOKEN
 */

/* استيرادٌ يتحمّل موضع الحزمة: `playwright` قد تكون مثبَّتةً عالمياً
   (NODE_PATH) لا في مجلّد المشروع. فيُجرَّب الاسم أوّلاً ثم المسار
   العالميّ، ويُقال السبب صراحةً إن غابت — لا انهيارٌ بأثرٍ مكدسيّ. */
let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  const root = process.env.NODE_PATH?.split(":")[0] || "/usr/lib/node_modules";
  try {
    ({ chromium } = await import(`${root}/playwright/index.mjs`));
  } catch (e) {
    console.error("✖ الطبقة الحيّة تحتاج playwright:\n   npm i -D playwright   أو NODE_PATH=<مسار الحزم العامّة>");
    process.exit(2);
  }
}

const BASE = process.env.SP_URL || "http://127.0.0.1:8098";
const TOKEN = process.env.SP_TOKEN || "";
const PAGES = ["/portfolio", "/market", "/chart", "/governance", "/ai",
               "/calculators", "/reports", "/library", "/notifications", "/settings"];
const findings = [];
const note = (check, where, what) => findings.push({ check, where, what });

// ضجيجُ المختبر لا يُحسب عطباً: شهاداتٌ يعترضها وكيل الشبكة، وأصولٌ خارجية.
/* ضجيجُ البيئة لا يُحسب عطباً في التطبيق: شهاداتٌ يعترضها وكيل الشبكة،
   وأصولٌ خارجية (شعارات · رسوم TradingView) يحجبها مختبرٌ بلا إنترنت.
   وتُذكر هنا صراحةً لا تُبتلع عمومياً — فمرشِّحٌ واسع يُخفي عطباً حقيقياً. */
const NOISE = /ERR_CERT_AUTHORITY_INVALID|ERR_TUNNEL_CONNECTION_FAILED|favicon|net::ERR_(NAME_NOT_RESOLVED|INTERNET_DISCONNECTED|CONNECTION_|PROXY_)/;

const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || undefined,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});

async function freshPage(width) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  if (TOKEN) await ctx.addInitScript(t => localStorage.setItem("sp_token", t), TOKEN);
  return { ctx, page: await ctx.newPage() };
}

// ── B-ERRORS · B-BADVALUES · B-OVERFLOW · B-BLANK (D002 · D007) ──────────
for (const [width, dev] of [[1440, "كمبيوتر"], [390, "جوال"]]) {
  for (const theme of ["light", "dark"]) {
    const { ctx, page } = await freshPage(width);
    for (const path of PAGES) {
      const errs = [];
      const onErr = e => errs.push("استثناء: " + String(e).slice(0, 120));
      const onCon = m => { if (m.type() === "error" && !NOISE.test(m.text())) errs.push("سجلّ: " + m.text().slice(0, 120)); };
      page.on("pageerror", onErr); page.on("console", onCon);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" }).catch(e => errs.push("تعذّر الفتح: " + e.message.slice(0, 80)));
      await page.evaluate(t => { const r = document.documentElement;
        r.classList.toggle("light", t === "light"); r.classList.toggle("dark", t === "dark"); }, theme).catch(() => {});
      await page.waitForTimeout(3000);
      const probe = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        len: (document.body.innerText || "").trim().length,
        bad: [...new Set((document.body.innerText || "").match(/NaN|Infinity|undefined|\[object Object\]/g) || [])],
      })).catch(() => ({ overflow: 0, len: 0, bad: [] }));
      const at = `${dev}/${theme}${path}`;
      if (errs.length) note("B-ERRORS", at, errs.slice(0, 2).join(" | "));
      if (probe.len < 40) note("B-BLANK", at, `نصّ الصفحة ${probe.len} حرفاً`);
      if (probe.overflow > 4) note("B-OVERFLOW", at, `خروجٌ أفقيّ ${probe.overflow}px`);
      if (probe.bad.length) note("B-BADVALUES", at, `قيمةٌ معطوبة تظهر للقارئ: ${probe.bad.join(", ")}`);
      page.off("pageerror", onErr); page.off("console", onCon);
    }
    await ctx.close();
  }
}

// ── B-LABELS — تسميةٌ واحدة بقيمتين (D001) ───────────────────────────────
{
  const KEYS = ["إجمالي الثروة", "القيمة السوقية", "صافي الربح", "عائد المحفظة",
                "السيولة المتاحة", "إجمالي المدفوع", "القيمة المدفوعة",
                "العائد المركّب", "نسبة السيولة النقدية", "الأرباح غير المحققة",
                "التقييم العام", "صافي المساهمات"];
  const seen = new Map();
  const { ctx, page } = await freshPage(1440);
  for (const path of ["/portfolio", "/market", "/governance", "/reports", "/calculators"]) {
    await page.goto(BASE + path, { waitUntil: "domcontentloaded" }).catch(() => {});
    await page.waitForTimeout(3500);
    const pairs = await page.evaluate(keys => {
      const out = [];
      const walk = e => {
        const t = (e.textContent || "").trim();
        if (t.length > 60) { for (const c of e.children) walk(c); return; }
        if (keys.includes(t)) {
          let n = e.nextElementSibling, hops = 0, cur = e;
          while (!n && cur.parentElement && hops < 3) { cur = cur.parentElement; n = cur.nextElementSibling; hops++; }
          const v = (n?.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24);
          if (/\d/.test(v)) out.push([t, v]);
        }
        for (const c of e.children) walk(c);
      };
      walk(document.body);
      return out;
    }, KEYS).catch(() => []);
    for (const [k, v] of pairs) {
      if (!seen.has(k)) seen.set(k, new Map());
      const m = seen.get(k);
      if (!m.has(v)) m.set(v, new Set());
      m.get(v).add(path);
    }
  }
  for (const [k, vals] of seen) {
    if (vals.size > 1) {
      const detail = [...vals].map(([v, ps]) => `${v} (${[...ps].join("،")})`).join("  ≠  ");
      note("B-LABELS", "عبر الشاشات", `«${k}» بقيمتين: ${detail}`);
    }
  }
  await ctx.close();
}

// ── B-CLEAN-DEVICE — إعدادٌ يُحفظ ولا يعبر (D003) ─────────────────────────
if (TOKEN) {
  const { ctx, page } = await freshPage(1280);
  await page.goto(BASE + "/portfolio", { waitUntil: "domcontentloaded" }).catch(() => {});
  await page.waitForTimeout(2500);
  const before = await page.evaluate(async tok => {
    const r = await fetch("/api/v1/settings/layout", { headers: { Authorization: "Bearer " + tok } });
    return (await r.json())?.data || {};
  }, TOKEN).catch(() => ({}));
  for (const target of ["reports", "governance"]) {
    await page.evaluate(async ({ t, tok }) => {
      await fetch("/api/v1/settings/layout", { method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + tok },
        body: JSON.stringify({ startPage: t }) });
    }, { t: target, tok: TOKEN }).catch(() => {});
    const { ctx: c2, page: p2 } = await freshPage(1280);
    await p2.goto(BASE + "/", { waitUntil: "domcontentloaded" }).catch(() => {});
    await p2.waitForTimeout(3200);
    const landed = new URL(p2.url()).pathname;
    if (landed !== "/" + target) {
      note("B-CLEAN-DEVICE", "جهازٌ نظيف",
           `صفحة البداية «${target}» محفوظة، والتطبيق استقرّ على ${landed}`);
    }
    await c2.close();
  }
  // نُعيد ما كان — الفحص لا يترك أثراً في إعدادات المالك
  await page.evaluate(async ({ b, tok }) => {
    await fetch("/api/v1/settings/layout", { method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + tok },
      body: JSON.stringify(b) });
  }, { b: before, tok: TOKEN }).catch(() => {});
  await ctx.close();
}

await browser.close();

const groups = [...new Set(findings.map(f => f.check))];
console.log(`لجنة كشف الأعطال — الطبقة الحيّة (${PAGES.length} شاشات × مظهرين × مقاسين)\n`);
for (const c of ["B-ERRORS", "B-BLANK", "B-OVERFLOW", "B-BADVALUES", "B-LABELS", "B-CLEAN-DEVICE"]) {
  const n = findings.filter(f => f.check === c).length;
  console.log(`  ${n ? "✖" : "✔"} ${c.padEnd(16)} ${n || "نظيف"}`);
}
if (findings.length) {
  console.log(`\n${findings.length} ملاحظة:`);
  for (const f of findings.slice(0, 40)) console.log(`  • [${f.check}] ${f.where}\n      ${f.what}`);
} else {
  console.log("\n✔ لا ملاحظات.");
}
process.exit(findings.length ? 1 : 0);
