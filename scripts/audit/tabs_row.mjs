/**
 * D164 — صفُّ التبويبات صفٌّ واحدٌ بلا إطارٍ في كلِّ مكانٍ يُعرض فيه سهم.
 *
 * كانت `CompanyPage` صفّاً واحداً بلا إطار و`StockView` عمودين مؤطَّرين،
 * وكلاهما يعرض الورقةَ نفسَها — فرأى المالكُ شكلين لشاشةٍ واحدة وقال
 * «لم يتغيّر شيء» وهو ينظر إلى المكوّن الآخر.
 *
 * فحصٌ بالقياس لا بقراءة الرمز: يفتح المكوّنَ الحقيقيَّ على أربعة عروضٍ
 * ويقيس من الـDOM عددَ الصفوف والفيضَ الأفقيَّ وعرضَ الأُطر وارتفاعَ
 * أصغرِ هدفِ لمس. فلا تكفي مطابقةُ الأصناف في النصّ.
 *
 * التشغيل:
 *   cd frontend && npx vite --port 5199 --strictPort &
 *   node scripts/audit/tabs_row.mjs
 */
/* استيرادٌ يتحمّل موضع الحزمة — كما في `browser.mjs`. */
let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  const root = process.env.NODE_PATH?.split(":")[0] || "/usr/lib/node_modules";
  try {
    ({ chromium } = await import(`${root}/playwright/index.mjs`));
  } catch {
    console.log("⚠ playwright غير متوفّر — تُخطّى هذه الطبقة (npm i -D playwright).");
    process.exit(0);
  }
}
const PAGE = process.env.PROBE_URL || 'http://localhost:5199/probe.html';
const b = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || '/opt/pw-browsers/chromium' });
let fail = 0;
for (const w of [360, 390, 768, 1280]) {
  const p = await b.newPage({ viewport: { width: w, height: 900 } });
  await p.goto(PAGE, { waitUntil: 'networkidle' });
  await p.waitForSelector('[role="tablist"]', { timeout: 15000 });
  const r = await p.evaluate(() => {
    const list = document.querySelector('[role="tablist"]');
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const tops = new Set(tabs.map(t => Math.round(t.getBoundingClientRect().top)));
    const cs = getComputedStyle(list);
    return {
      count: tabs.length,
      rows: tops.size,
      overflow: list.scrollWidth - list.clientWidth,
      bodyOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      borders: tabs.map(t => getComputedStyle(t).borderTopWidth + '/' + getComputedStyle(t).borderLeftWidth),
      minH: Math.min(...tabs.map(t => Math.round(t.getBoundingClientRect().height))),
      labels: tabs.map(t => t.innerText.trim()),
      listBottom: cs.borderBottomWidth,
      clipped: tabs.some(t => t.scrollWidth > t.clientWidth + 1),
    };
  });
  const ok = r.count === 6 && r.rows === 1 && r.overflow <= 0 && r.bodyOverflow <= 0
           && r.borders.every(x => x === '0px/0px') && r.minH >= 32 && !r.clipped;
  if (!ok) fail = 1;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${w}px  أزرار=${r.count} صفوف=${r.rows} فيض=${r.overflow} فيض_الصفحة=${r.bodyOverflow} أدنى_ارتفاع=${r.minH} أطر=${[...new Set(r.borders)]} قصّ=${r.clipped}`);
  console.log(`        ${r.labels.join(' · ')}`);
  await p.close();
}
await b.close();
process.exit(fail);
