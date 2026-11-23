/* ══ رمزٌ واحدٌ لكلّ ما يُكتب في البحث ══ (‏D787 — المالك 2026-11-23)
   «في كلّ شاشةٍ بحث: أضغط تاسي، أو أضع رمزَ شركة، أو رمزَ العقد نفسِه فيفتح — الرمزُ المختصرُ للسهم في السوقين، أو رمزُ العقد».
   فما يُكتب أو يُلصق يُطبَّع هنا مرّةً: الأرقامُ العربيةُ لاتينية، وبادئةُ السوق تُرفع (‏TADAWUL: · NASDAQ: · OPRA:)، و«تاسي» مؤشّرُها،
   والرباعيُّ سعوديٌّ بلاحقته، والعقدُ بصيغتيه (‏OCC وتريدنق فيو) رمزُ OCC، والباقي رمزٌ أمريكيٌّ كما هو. وما لا يُفهم null — لا يُخمَّن. */
import { toOcc } from "./options";

const AR_DIGITS = /[٠-٩]/g;
const latin = (s: string) => s.replace(AR_DIGITS, d => String(d.charCodeAt(0) - 0x0660));

export function normalizeSymbol(raw: string): string | null {
  let s = latin(String(raw || "")).trim();
  if (!s) return null;
  if (/^(تاسي|تاسى|مؤشر السوق|المؤشر العام)$/.test(s)) return "^TASI.SR";
  s = s.toUpperCase().replace(/\s+/g, "");
  const occ = toOcc(s);
  if (occ) return occ;
  s = s.replace(/^[A-Z]{2,10}:/, "");                     // ‏TADAWUL:1120 · NASDAQ:NVDA · TVC:…
  if (s === "TASI" || s === "^TASI" || s === "TASI.SR" || s === "^TASI.SR") return "^TASI.SR";
  if (/^\d{4}(\.SR)?$/.test(s)) return `${s.slice(0, 4)}.SR`;
  const occ2 = toOcc(s);
  if (occ2) return occ2;
  if (/^\^?[A-Z][A-Z0-9.\-=]{0,11}$/.test(s)) return s;     // ‏NVDA · BRK.B · ^GSPC · BTC-USD · CL=F
  return null;
}

/** نسخٌ إلى الحافظة — وللمتصفّحات التي تمنعه (‏iOS القديم · غيرُ الآمن) نسخٌ بحقلٍ مخفيّ */
export async function copyText(t: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); return true; }
  } catch { /* يُجرَّب الاحتياط */ }
  try {
    const ta = document.createElement("textarea");
    ta.value = t; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0"; ta.style.top = "0";
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, t.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch { return false; }
}
