// حارسُ D513: العنوانُ ورقمُه في الحاوية الموسَّطة على محورٍ واحد (بأمر المالك).
// يُرسم ترميزُ «Metric» بـglobals.css الحقيقيّ في المتصفّح، ويُقاس مركزُ الاثنين.
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(ROOT, "frontend", "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const css = readFileSync(new URL("../../frontend/src/styles/globals.css", import.meta.url), "utf8")
  .replace(/@tailwind[^;]*;|@import[^;]*;|@apply[^;]*;/g, "");
const html = `<!doctype html><html dir="rtl"><head><style>${css}
.text-center{text-align:center}</style></head><body style="width:390px">
<div style="display:grid;grid-template-columns:repeat(3,1fr);width:360px">
  <div class="text-center"><div id="l">3 أشهر</div><div id="v" class="tabular-nums" dir="ltr">+0.16%</div></div>
</div></body></html>`;
const b = await chromium.launch({ executablePath: CHROME });
const p = await b.newPage();
await p.setContent(html);
const c = async (id) => p.$eval(id, (e) => { const r = document.createRange(); r.selectNodeContents(e); const q = r.getBoundingClientRect(); return q.left + q.width / 2; });
const dl = await c("#l"), dv = await c("#v");
await b.close();
const ok = Math.abs(dl - dv) < 3;
console.log(`${ok ? "PASS" : "FAIL"} D513 العنوانُ ورقمُه على محورٍ واحد في الحاوية الموسَّطة — فرقُ المركزين ${Math.abs(dl - dv).toFixed(1)}px`);
process.exit(ok ? 0 : 1);
