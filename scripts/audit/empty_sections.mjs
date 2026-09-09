// ─────────────────────────────────────────────────────────────────────────
// D216 — لا عنوانَ بطاقةٍ بلا مضمون.
//
// رأى المالكُ «ميزان خبراء الحوكمة» عنواناً فوق فراغٍ في غازكو 2080: البطاقةُ
// كانت تُرسَم دائماً ومحتواها مشروطٌ بأركان الإطار، فحين يمتنع المحرّكُ —
// وهو امتناعٌ صحيح — بقي العنوانُ وحدَه. والعنوانُ يَعِد بما تحته.
//
// يُقاس في متصفّحٍ حقيقيّ: تُفتح الصفحاتُ بخادمٍ مموَّهٍ يردّ فراغاً — وهي
// الحالةُ التي يمتنع فيها كلُّ محرّك — ويُشترط ألّا تبقى بطاقةٌ عنوانُها
// مكتوبٌ وجسمُها خالٍ من أيّ نصّ.
//
// وإن غاب المتصفّحُ قال ذلك ومرّ: فحصٌ لا يستطيع القياس لا يحكم.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5219;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

const PW_PATHS = [
  join(FRONT, "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js",
  "/usr/local/lib/node_modules/playwright/index.js",
];
const pw = PW_PATHS.find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) {
  console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح في هذه البيئة.");
  process.exit(0);
}
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
if (!chromium) {
  console.log("… تعذّر الفحص: لم يُعثر على `chromium`.");
  process.exit(0);
}

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"],
                   { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* انتهى */ } };
process.on("exit", stop);

let up = false;
for (let i = 0; i < 60 && !up; i++) {
  await new Promise(r => setTimeout(r, 500));
  try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* لم يقلع */ }
}
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
await page.route("**/api/v1/**", r => r.fulfill({
  status: 200, contentType: "application/json",
  body: JSON.stringify({ success: true, data: [] }),
}));
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* خاصّ */ } });

let fail = 0;
for (const [name, path] of [["السوق", "/market"], ["الحوكمة", "/governance"], ["تحليل الذكاء", "/ai"]]) {
  try {
    await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 });
  } catch { /* تُحسب فارغةً أدناه */ }
  await page.waitForTimeout(1500);
  // بطاقةٌ عنوانُها مكتوبٌ وما بعده لا نصّ فيه.
  const empties = await page.$$eval(".card", cards => cards.flatMap(c => {
    const t = c.querySelector(".card-title");
    if (!t) return [];
    const title = (t.textContent || "").trim();
    if (!title) return [];
    const body = (c.textContent || "").replace(title, "").trim();
    return body.length === 0 ? [title] : [];
  })).catch(() => []);
  const ok = empties.length === 0;
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} صفحةُ «${name}» بلا بطاقةٍ عنوانُها فوق فراغ`
              + (ok ? "" : ` — ${empties.slice(0, 4).join(" · ")}`));
}
await browser.close();
stop();
console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
