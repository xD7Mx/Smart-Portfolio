/* ══ عقودُ الخيارات — قراءةُ رمز العقد (‏OCC) ══ (‏D747)
   الرمزُ: الأصلُ ثمّ الأجلُ (سنة شهر يوم) ثمّ النوعُ (C شراء · P بيع) ثمّ سعرُ التنفيذ × 1000 — مثل SPY261120C00600000. */
export type OptionInfo = { root: string; expiry: string; type: "call" | "put"; strike: number };

const RX = /^([A-Z]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$/;
const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];

export function parseOption(sym: string): OptionInfo | null {
  const m = RX.exec(String(sym || "").toUpperCase());
  if (!m) return null;
  return { root: m[1], expiry: `20${m[2]}-${m[3]}-${m[4]}`, type: m[5] === "C" ? "call" : "put", strike: Number(m[6]) / 1000 };
}

export const isOption = (sym: string) => RX.test(String(sym || "").toUpperCase());

export function dayMonth(iso: string): string {
  const [, mo, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[mo - 1]}`;
}

/** الأيامُ الباقية بكلامٍ عربيّ: «اليوم» · «غداً» · «بعد يومين» · «بعد 5 أيام» · «بعد 12 يوماً» */
export function dteLabel(dte: number): string {
  if (dte <= 0) return "اليوم";
  if (dte === 1) return "غداً";
  if (dte === 2) return "بعد يومين";
  if (dte <= 10) return `بعد ${dte} أيام`;
  return `بعد ${dte} يوماً`;
}

export function daysTo(iso: string, now = new Date()): number {
  const [y, mo, d] = iso.split("-").map(Number);
  const t = Date.UTC(y, mo - 1, d), n = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.round((t - n) / 864e5);
}

const strikeTxt = (k: number) => (Number.isInteger(k) ? String(k) : k.toFixed(2).replace(/0$/, ""));

/** «SPY 600 شراء» — وتحته «20 نوفمبر · بعد 5 أيام» */
export function optionTitle(o: OptionInfo): string {
  return `${o.root} ${strikeTxt(o.strike)} ${o.type === "call" ? "شراء" : "بيع"}`;
}
export function optionSub(o: OptionInfo, now = new Date()): string {
  const n = daysTo(o.expiry, now);
  return n < 0 ? `انتهى ${dayMonth(o.expiry)}` : `${dayMonth(o.expiry)} · ${dteLabel(n)}`;
}
