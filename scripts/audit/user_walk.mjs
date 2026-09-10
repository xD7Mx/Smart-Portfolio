// ─────────────────────────────────────────────────────────────────────────
// البند ٣٢ + أمرُ المالك — حارسٌ يتقمّص المستخدم.
//
// «لا يكون الاعتماد على المستخدم أن يلاحظ شيئاً حتى تأخذه بعين الاعتبار.»
//
// كلُّ حارسٍ سابقٍ يفحص **وحدةً**: دالّةً أو صفحةً أو قاعدة. وهذا يفحص
// **رحلة**: يفتح التطبيقَ كما يفتحه المالك، ويتنقّل بين الشاشات والتبويبات
// ببياناتٍ تُشبه الواقع، ويسأل في كلّ محطّةٍ ما يسأله هو بعينه:
//
//   · أثمّة خطأٌ في الصفحة يُطفئ ما بعده؟
//   · أثمّة قيمةٌ معطوبةٌ تُقرأ (‏NaN · undefined · [object Object] · Infinity)؟
//   · أثمّة عنوانٌ فوق فراغ؟
//   · أيتناقض التطبيقُ مع نفسه — حكمٌ في شاشةٍ يخالف حكمَه في أخرى؟
//   · أزرٌّ يَعِد ولا يفعل؟
//
// وما وجده يُسمّى بالشاشة والنصّ، لا «فيه خطأ».
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5223;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

const PW = [
  join(FRONT, "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js",
].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) {
  console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح في هذه البيئة.");
  process.exit(0);
}
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
if (!chromium) { console.log("… لا chromium."); process.exit(0); }

let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

/* ══ بياناتٌ تُشبه الواقع لا قوائمَ فارغة ══
   الخادمُ المموَّه الذي يردّ `[]` لكلّ شيء يُخفي أعطابَ العرض: لا رقمَ
   يُقسَم ولا حكمَ يُقارَن. فتُبنى محفظةٌ صغيرةٌ كاملةُ الحقول. */
const DECISION = { label: "احتفاظ", color: "amber", reason: "الدرجة متوسطة والسعر قرب القيمة" };
const CO = (symbol, name, price, w, tw) => ({
  company_id: symbol === "2222" ? 1 : 2, symbol, name, company_name: name,
  market_value: price * 1000, current_weight: w, target_weight: tw,
  last_price: price, dividend_yield: 4.2, sector: "الطاقة",
  // الحكمُ الشرعيّ في صفّ القرار (‏D232) — شاهدُ الهلال في جدول التوزيع.
  sharia_status: "COMPLIANT",
});
const ALLOC = {
  items: [CO("2222", "أرامكو", 26, 12, 10), CO("4190", "جرير", 16, 4, 10)],
  total_market_value: 42000, available_cash: 58000, fresh_cash: 58000,
  reinvestment_pool: 0,
};
const ANALYSIS = {
  symbol: "2222", name: "أرامكو", price: 26.04, change_pct: -0.08,
  day_low: 26.02, day_high: 26.2,
  fair_value: 30.5, fair_value_upside_pct: 17.1,
  fundamentals: { market_cap: 6.3e12, revenue: 1.6e12, net_income: 3.5e11,
                  eps: 1.44, pe_ratio: 18.1, dividend_yield: 6.0,
                  // هدفُ المحلّلين في البطاقة نفسِها — بجانبه توضع الخانة.
                  target_mean_price: 30.5, book_value: 6.4 },
  technical: { rsi: 49, trend: "محايد", support: 25, resistance: 28 },
  governance: { score: 81 }, ai_score: 81, score: 81,
  decision: DECISION, evaluable: true,
  // ══ القيمةُ النسبيةُ **مع** هدفِ المحلّلين ══ (D232)
  // الحالةُ التي كانت مستحيلةً قبل أمر المالك: هدفٌ موجودٌ وقيمةٌ نسبيةٌ
  // معه. فيُقاس أنها تظهر في موضعها الدائم ولا تُدسّ في خانة الهدف.
  rel_value: 28.4, rel_low: 24.1, rel_high: 33.0, rel_conf: "متوسطة",
  rel_basis: "التقييم النسبي", rel_upside_pct: 9.1,
  rel_confidence_why: ["نظائر 6"],
  // مقارنةُ السهم بقطاعه — حكمُها هو النصُّ الذي أمر المالكُ بنقله.
  valuation: { sector: "الطاقة", verdict: "أرخص من متوسط القطاع",
               pe: 18.1, sector_avg_pe: 21.4, pb: 2.1, sector_avg_pb: 2.6 },
  governance_standard: { metrics: [{ key: "roe", label: "العائد على حقوق الملكية", value: 24.1, unit: "%" }] },
};
/* قوائمُ ثلاثِ سنواتٍ — مقياسا القيمة النسبية (ربحيةُ السهم والدفترية)
   سطرانِ فيها، وهو سببُ كون هذا موضعَها. */
const FINANCIALS = {
  years: [2022, 2023, 2024],
  periods: [1, 2, 3].map(i => ({
    revenue: 1.5e12 + i * 1e11, net_income: 3.0e11 + i * 2e10,
    eps: 1.2 + i * 0.1, equity: 1.4e12, book_value: 6.0 + i * 0.2,
    debt_ratio: 22.4, interest_coverage: 18.2,
    operating_cash_flow: 5.0e11, free_cash_flow: 2.2e11, ending_cash: 1.1e11,
  })),
  changes: { revenue: 6.2, net_income: 4.1, eps: 3.9 },
  verdict: "قوائم متينة", verdict_tone: "green", finance_score: 81,
};
/* حالةُ الامتناع: قطاعٌ بلا نظائرَ كافية — الخانةُ تبقى وتقول سببَها. */
const ANALYSIS_BARE = {
  ...ANALYSIS, rel_value: null, rel_low: null, rel_high: null,
  rel_conf: null, rel_upside_pct: null, rel_confidence_why: [],
  rel_why: "لا نظائرَ كافيةً في القطاع",
};
const body = (data) => ({ status: 200, contentType: "application/json",
                          body: JSON.stringify({ success: true, data }) });

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"],
                   { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* انتهى */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  await new Promise(r => setTimeout(r, 500));
  try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* بعد */ }
}
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); stop(); process.exit(0); }

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
const errors = [];
let bare = false;                 // تُضبط قبل كلّ محطّة من مسارها
page.on("pageerror", e => errors.push(String(e).split("\n")[0].slice(0, 120)));
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (/\/allocation(\?|$)/.test(u)) return r.fulfill(body(ALLOC));
  if (/\/market\/company\//.test(u) || /\/ai\/stock-opinion\//.test(u))
    return r.fulfill(body(bare ? ANALYSIS_BARE : ANALYSIS));
  if (/\/market\/financials\//.test(u)) return r.fulfill(body(FINANCIALS));
  if (/\/holdings(\?|$)/.test(u)) return r.fulfill(body(ALLOC.items.map((it, i) => ({
    id: i + 1, company_id: it.company_id, symbol: it.symbol,
    company: { id: it.company_id, symbol: it.symbol, company_name: it.name },
    quantity: 1000, market_value: it.market_value, last_price: it.last_price,
    average_price: it.last_price * 0.9, unrealized_profit_pct: 8,
  }))));
  return r.fulfill(body([]));
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* خاصّ */ } });

/* ══ ما يقرؤه المستخدمُ ولا يجوز أن يراه ══
   قيمةٌ معطوبةٌ تصل الشاشةَ تعني حساباً انكسر بصمت. و«‏-» و«غير متوفّر»
   مقبولتان: امتناعٌ مُعلَن، لا كسرٌ مستور. */
const BROKEN = /\bNaN\b|\bundefined\b|\[object Object\]|\bInfinity\b/;

/* ما يجب أن يظهر في كلّ شاشةٍ من البيانات المموَّهة — شاهدُ وصولها. */
const WANT = {
  "المحفظة": "أرامكو",
  "جدول التوزيع": "أرامكو",
};

const STOPS = [
  ["لوحة التحكّم", "/"],
  ["المحفظة", "/portfolio"],
  ["السوق", "/market"],
  ["الحوكمة", "/governance"],
  ["تحليل الذكاء", "/ai"],
  ["جدول التوزيع", "/probe-alloc.html"],
  ["البيانات المالية", "/probe-fin.html"],
  ["مقارنة القطاع", "/probe-panel.html"],
  ["مقارنة القطاع (بلا نظائر)", "/probe-panel.html?bare=1"],
];

const seenDecisions = new Set();
for (const [name, path] of STOPS) {
  errors.length = 0;
  bare = /bare=1/.test(path);
  try {
    await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 });
  } catch (e) { errors.push("تعذّر الفتح: " + String(e).slice(0, 60)); }
  await page.waitForTimeout(1600);
  const text = ((await page.textContent("body").catch(() => "")) || "").trim();

  say(errors.length === 0, `«${name}» بلا خطأٍ يُطفئ الصفحة`, errors[0] || "");
  say(text.length > 0, `«${name}» تُرسَم بمحتوى`, `${text.length} حرفاً`);

  /* ══ ولا يكفي أن تُرسَم: يجب أن تصلها البيانات ══
     صفحةٌ تُرسَم بقشرتها وحدَها تمرّ كلَّ الفحوص السابقة وهي فارغةٌ من
     المعنى — والفحصُ الذي يمرّ على فراغٍ لا يفحص شيئاً (البند ٣١). */
  if (WANT[name]) {
    say(text.includes(WANT[name]), `«${name}» وصلتها بياناتُ المحفظة`,
        text.includes(WANT[name]) ? WANT[name] : `لم يظهر «${WANT[name]}»`);
  }

  const bad = text.match(BROKEN);
  say(!bad, `«${name}» بلا قيمةٍ معطوبةٍ تُقرأ`, bad ? `وجد «${bad[0]}»` : "");

  const empties = await page.$$eval(".card", cards => cards.flatMap(c => {
    const t = c.querySelector(".card-title");
    if (!t) return [];
    const title = (t.textContent || "").trim();
    if (!title) return [];
    return (c.textContent || "").replace(title, "").trim().length === 0 ? [title] : [];
  })).catch(() => []);
  say(empties.length === 0, `«${name}» بلا عنوانٍ فوق فراغ`, empties.slice(0, 3).join(" · "));

  // حكمُ التطبيق حيث ظهر — يُجمع ليُقارَن بين الشاشات.
  for (const w of ["شراء قوي", "شراء", "احتفاظ", "تخفيف", "تجنّب", "بيانات غير كافية"]) {
    if (text.includes(w)) { seenDecisions.add(w); break; }
  }

  // زرٌّ يَعِد ولا يفعل: كلُّ زرٍّ ظاهرٍ له نصٌّ أو وصفٌ مسموع.
  const mute = await page.$$eval("button", bs => bs.filter(b => {
    const r = b.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) return false;
    return !((b.textContent || "").trim() || b.getAttribute("aria-label")
             || b.getAttribute("title"));
  }).length).catch(() => 0);
  say(mute === 0, `«${name}» بلا زرٍّ صامتٍ بلا اسم`, mute ? `${mute} زرّاً` : "");

  /* ══ موضعُ القيمة النسبية الدائم ══ (D232 · بأمر المالك)
     الحالةُ المقيسة: هدفُ المحلّلين موجودٌ (‏30.5) والقيمةُ النسبيةُ معه
     (‏28.4). فتُشترط ثلاثةٌ في متصفّحٍ حقيقيّ: أنها تظهر أصلاً — وهذا هو
     الدوام —، وأنها باسمها لا باسم «القيمة العادلة»، وأن رقمَها هو
     المعروضُ في موضعها لا رقمُ الهدف. */

  /* ══ هويّةُ الصفّ في جدول التوزيع ══ (بأمر المالك · D232)
     الجدولُ أمرُ تنفيذ، فيُقاس أن الشعارَ والهلالَ وصلا الصفَّ فعلاً —
     صورةٌ (أو حرفٌ بديلٌ عند تعذّرها) وهلالٌ بتلميحِ حكمه. */
  if (name === "مقارنة القطاع") {
    /* ══ الحكمُ تحت العنوان لا يسارَ البطاقة ══ (بأمر المالك · D233)
       يُقاس بالهندسة لا بالنصّ: صندوقُ الحكم أسفلُ من صندوق العنوان،
       وحافّتُه اليمنى قريبةٌ من حافّته — أي في عمود العنوان لا في الطرف
       المقابل. وفي RTL البدايةُ يميناً، فالتباعدُ يُقاس بفرق الحافّتين. */
    const geo = await page.evaluate(() => {
      const titles = [...document.querySelectorAll(".card-title")]
        .filter(t => (t.textContent || "").includes("التقييم مقابل القطاع"));
      if (!titles.length) return null;
      const t = titles[0];
      const card = t.closest(".card");
      const v = [...(card ? card.querySelectorAll("*") : [])]
        .find(e => (e.textContent || "").trim() === "أرخص من متوسط القطاع");
      if (!v) return null;
      const a = t.getBoundingClientRect(), b = v.getBoundingClientRect();
      return { below: b.top >= a.bottom - 2, dx: Math.abs(b.right - a.right) };
    });
    say(!!geo, "حكمُ مقارنة القطاع ظاهرٌ ليُقاس موضعُه");
    if (geo) {
      say(geo.below, "الحكمُ أسفلَ العنوان لا في سطره");
      say(geo.dx < 40, "وفي عمود العنوان لا في الطرف المقابل",
          `فرقُ الحافّتين ${Math.round(geo.dx)}px`);
    }
    say(text.includes("التقييم النسبي"),
        "والتقييمُ النسبيُّ في تبويب مقارنة القطاع أيضاً");

    /* ══ خانةٌ دائمةٌ في بطاقة «البيانات المالية» ══ (بأمر المالك · D234)
       لا في جدول السنوات: موضعُها البطاقةُ التي فيها المكرّرُ وهدفُ
       المحلّلين — أي مُدخَلاها والرقمُ الذي تُقرأ بجانبه. ويُقاس أنها
       **داخل تلك البطاقة** لا في أخرى، وأن رقمَها هو المعروضُ فيها. */
    const kpi = await page.evaluate(() => {
      const card = [...document.querySelectorAll(".card")].find(c => {
        const t = c.querySelector(".card-title");
        return t && (t.textContent || "").trim() === "البيانات المالية";
      });
      if (!card) return null;
      const cell = [...card.querySelectorAll(".kpi")].find(k =>
        ((k.querySelector(".kpi-lbl") || {}).textContent || "").trim()
          === "التقييم النسبي");
      if (!cell) return { found: false };
      const val = (cell.querySelector(".kpi-val") || {}).textContent || "";
      const peers = [...card.querySelectorAll(".kpi-lbl")]
        .map(l => (l.textContent || "").trim());
      return { found: true, val: val.trim(),
               withPE: peers.some(l => l.includes("مكرر الربحية")),
               withTarget: peers.some(l => l.includes("تقدير المحللين")) };
    });
    say(!!kpi && kpi.found === true,
        "خانةُ التقييم النسبيّ داخل بطاقة «البيانات المالية»");
    if (kpi && kpi.found) {
      say(kpi.val.includes("28.4"), "ورقمُها هو المعروضُ فيها", kpi.val);
      say(kpi.withPE && kpi.withTarget,
          "وبجانبِ المكرّر وهدفِ المحلّلين — لا في بطاقةٍ أخرى");
    }
  }

  /* والدوامُ يُقاس في حالة الامتناع أيضاً: خانةٌ تُطوى عند الغياب تُخفي
     الميزةَ ويظنّها المستخدمُ خاصّةً ببعض الشركات. */
  if (name === "مقارنة القطاع (بلا نظائر)") {
    const bareCell = await page.evaluate(() => {
      const card = [...document.querySelectorAll(".card")].find(c => {
        const t = c.querySelector(".card-title");
        return t && (t.textContent || "").trim() === "البيانات المالية";
      });
      if (!card) return null;
      const cell = [...card.querySelectorAll(".kpi")].find(k =>
        ((k.querySelector(".kpi-lbl") || {}).textContent || "").trim()
          === "التقييم النسبي");
      return cell ? ((cell.querySelector(".kpi-val") || {}).textContent || "").trim() : null;
    });
    say(!!bareCell, "الخانةُ باقيةٌ حيث يمتنع التقييم — لا تُطوى");
    say(!!bareCell && bareCell.includes("لا نظائر"),
        "وتقول سببَ امتناعها لا رقماً ضعيفاً", String(bareCell));
  }

  if (name === "جدول التوزيع") {
    // الشعارُ يُقاس بصفّه لا بنجاح الشبكة: `co-logo` تحمله الصورةُ
    // وبديلُها الحرفيّ معاً، فلا يمرّ الفحصُ ولا يسقط لأجل مزوّدٍ محجوب.
    const logos = await page.$$eval("table .co-logo", els => els.length).catch(() => 0);
    say(logos >= 2, "صفوفُ جدول التوزيع تحمل شعارَ الشركة",
        `${logos} شعاراً لصفّين`);
    const moons = await page.$$eval("table [title]", els =>
      els.filter(e => /متوافقة|مختلطة|نقية|غير متوافقة/.test(e.getAttribute("title") || "")).length
    ).catch(() => 0);
    say(moons > 0, "والهلالُ يقول حكمَه في تلميحه", `${moons} هلالاً`);
  }
}

/* ══ العقلُ الواحد ══ (‏D166)
   حكمٌ واحدٌ للورقة الواحدة في كلّ شاشة. وتعدُّدُ الأحكام المعروضة على
   بياناتٍ واحدة يعني مُنتِجَين — وهو ما مُنع. */
/* ولا يُقال «نظيف» عن حكمٍ لم يظهر: فحصٌ يمرّ على فراغٍ يُطمئن كاذباً،
   فيُعلَن تعذّرُ القياس بصراحة ولا يُعدّ نجاحاً. */
if (seenDecisions.size === 0) {
  console.log("…  حكمُ التطبيق لم يظهر في هذه الرحلة — لا يُقاس اتّساقُه، ولا يُعدّ نجاحاً.");
} else {
  say(seenDecisions.size === 1, "حكمٌ واحدٌ عبر الشاشات على البيانات نفسها",
      [...seenDecisions].join(" · "));
}

await browser.close();
stop();
console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
