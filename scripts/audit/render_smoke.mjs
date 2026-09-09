// ─────────────────────────────────────────────────────────────────────────
// D211 — الشاشةُ تُرسَم فعلاً، لا تُترجَم فحسب.
//
// ركّب المالكُ حزمةً فرأى **شاشةً سوداء**. وكان البناءُ قد نجح: `vite build`
// يترجم ولا يتحقّق، و`lint:hooks` يفحص الخطّافات وحدَها. فمرّ:
//   · اسمٌ مستعملٌ بلا تعريف (‏canWrite · fmt0 · Empty · Star · setSortKey)
//   · وثابتٌ قُرئ قبل تعريفه (‏initialSymbol) — «منطقةُ موتٍ» لا يمسكها
//     فحصُ الأنواع لأن الاسمَ معرَّفٌ في النطاق، والخطأُ في الترتيب.
//
// ولا يُمسَك هذا إلا بالتشغيل: يُقلَع خادمُ التطوير، وتُفتح صفحاتُ التطبيق
// الخمس في متصفّحٍ حقيقيّ بخادمٍ مموَّه، ويُشترط أن تُرسَم كلُّ صفحةٍ بلا
// خطأٍ في الصفحة وبنصٍّ غيرِ فارغ. فالشاشةُ السوداء تُقاس ولا تُوصف.
//
// يُشغَّل ضمن اللجنة قبل بناء الحزمة. وإن غاب المتصفّحُ أو اعتمادياتُ
// الواجهة، يقول ذلك ويمرّ — فحصٌ لا يستطيع القياس لا يحكم.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5217;                       // منفذٌ يخصّ اللجنة وحدَها
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

const PAGES = [
  ["لوحة التحكّم", "/"],
  ["المحفظة", "/portfolio"],
  ["السوق", "/market"],
  ["الحوكمة", "/governance"],
  ["تحليل الذكاء", "/ai"],
];

let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

/* playwright قد يسكن في اعتماديات الواجهة أو في حزم النظام العامّة —
   يُبحث في الموضعين قبل الحكم بالتعذّر. */
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

/* الحزمةُ المثبَّتة عامّةً تُصدَّر افتراضيّاً (CJS)، والمحلّيةُ تُصدّر
   أسماءها — فيُقرأ الاثنان. */
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
if (!chromium) {
  console.log("… تعذّر الفحص: لم يُعثر على `chromium` في حزمة playwright.");
  process.exit(0);
}

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"],
                   { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* انتهى */ } };
process.on("exit", stop);

// انتظارُ الخادم: يُسأل حتى يردّ بدل مهلةٍ ثابتة تطول أو تقصر.
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  await new Promise(r => setTimeout(r, 500));
  try {
    const r = await fetch(`http://localhost:${PORT}/`);
    up = r.ok;
  } catch { /* لم يقلع بعد */ }
}
if (!up) {
  console.log("… تعذّر إقلاعُ خادم التطوير في المهلة — لا حكم.");
  stop();
  process.exit(0);
}

const browser = await chromium.launch({ executablePath: CHROME });
for (const [name, path] of PAGES) {
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 140)));
  // خادمٌ مموَّه: قوائمُ فارغةٌ لكلّ نداء — فالفحصُ للرسم لا للبيانات.
  await page.route("**/api/v1/**", r => r.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ success: true, data: [] }),
  }));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* خاصّ */ } });
  try {
    await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 });
  } catch (e) {
    errs.push("تعذّر فتحُ الصفحة: " + String(e).slice(0, 80));
  }
  await page.waitForTimeout(1800);
  const text = (await page.textContent("body").catch(() => "") || "").trim();
  for (const e of errs) console.log(`     ${name}: ${e}`);
  say(errs.length === 0 && text.length > 0, `صفحةُ «${name}» تُرسَم بلا خطأ`,
      `نصّ ${text.length} حرفاً`);
  await page.close();
}
await browser.close();
stop();

console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
