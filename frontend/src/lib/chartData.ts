/* بياناتُ الرسم البيانيّ — دوالُّ خالصةٌ يفحصها الحارسُ بنفسها (‏scripts/audit/pro_chart_d736.mjs).
   ══ ‏D736 (المالك 2026-11-15): «رسمٌ احترافيٌّ يغنيني عن تريدنق فيو… شموعٌ حقيقية… وخيارُ تخصيصٍ في الأطر» ══
   الخادمُ ينظّف الشموعَ (‏D735)، وهنا خطُّ الدفاع الثاني: المكتبةُ ترفض سلسلةً فيها زمنٌ مكرَّرٌ أو غيرُ مرتَّب فتُعرض فارغة —
   فلا تُسلَّم إلّا مرتَّبةً بلا تكرارٍ ولا شمعةٍ مختلّة. والوقتُ دون اليوم بتوقيت الرياض كما يكتبه الخادم: يُمرَّر «ساعةَ
   حائطٍ» فيقرأ المحورُ 10:00 لافتتاح الرياض (كان يُحوَّل إلى التوقيت العالميّ فيقرأ 07:00). */
export type RawBar = { date: string; open: number; high: number; low: number; close: number; volume?: number };
export type CBar = RawBar & { time: string | number };

/** «2026-11-12» يومٌ كما هو؛ و«2026-11-12 10:00» ثوانٍ بساعة حائط الرياض. */
export function barTime(date: string): string | number {
  const d = String(date || "");
  if (d.length <= 10) return d;
  return Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10), +d.slice(11, 13), +d.slice(14, 16)) / 1000;
}

/** مرتَّبةٌ بلا زمنٍ مكرَّر ولا شمعةٍ مختلّة (أرقامٌ موجبة، والقمّةُ والقاعُ يحويان الجسم) — وآخرُ المكرَّرَين يحكم. */
export function sanitizeBars(rows: RawBar[] | null | undefined): CBar[] {
  const ok = (v: any) => typeof v === "number" && isFinite(v) && v > 0;
  const by = new Map<string | number, CBar>();
  for (const r of rows || []) {
    if (!r || !r.date || !ok(r.open) || !ok(r.high) || !ok(r.low) || !ok(r.close)) continue;
    const hi = Math.max(r.high, r.open, r.close), lo = Math.min(r.low, r.open, r.close);
    const t = barTime(r.date);
    by.set(t, { ...r, high: hi, low: lo, volume: Number(r.volume) || 0, time: t });
  }
  const key = (t: string | number) => (typeof t === "number" ? t : Date.parse(t + "T00:00:00Z") / 1000);
  return [...by.values()].sort((a, b) => key(a.time) - key(b.time));
}

/* ── الإطارات ── الصيغةُ «عددٌ + وحدة» كما يقرؤها الخادم: m دقيقة · h ساعة · d يوم · wk أسبوع · mo شهر */
export type TfUnit = "m" | "h" | "d" | "wk" | "mo";
export const TF_UNITS: [TfUnit, string, string, number][] = [
  ["m", "دقيقة", "د", 240], ["h", "ساعة", "س", 24], ["d", "يوم", "ي", 30], ["wk", "أسبوع", "أ", 12], ["mo", "شهر", "ش", 12]];
export const TF_PRESETS = ["5m", "15m", "30m", "1h", "2h", "4h", "1d", "1wk", "1mo"];
export const TF_BAR = ["15m", "1h", "4h", "1d", "1wk", "1mo"];

export function parseTf(tf: string): { n: number; unit: TfUnit } | null {
  const m = /^(\d{1,3})(mo|wk|w|m|h|d)$/.exec(String(tf || "").trim().toLowerCase());
  if (!m) return null;
  let n = +m[1], unit = (m[2] === "w" ? "wk" : m[2]) as TfUnit;
  if (unit === "m" && n >= 60 && n % 60 === 0) { n = n / 60; unit = "h"; }
  const max = TF_UNITS.find(u => u[0] === unit)![3];
  return n >= 1 && n <= max ? { n, unit } : null;
}
export const tfKey = (n: number, unit: TfUnit) => `${n}${unit}`;
/** «4س» · «يوم» · «3ي» — الواحدُ من اليوم والأسبوع والشهر باسمه كاملاً. */
export function tfShort(tf: string): string {
  const p = parseTf(tf);
  if (!p) return tf;
  const u = TF_UNITS.find(x => x[0] === p.unit)!;
  return p.n === 1 && (p.unit === "d" || p.unit === "wk" || p.unit === "mo") ? u[1] : `${p.n}${u[2]}`;
}
/* العددُ والمعدودُ بالفصحى: «ساعة» · «ساعتان» · «6 ساعات» · «12 ساعة» — و«15 دقيقة» · «3 أيام» · «11 يوماً» */
const TF_WORDS: Record<TfUnit, [string, string, string]> = {
  m: ["دقيقتان", "دقائق", "دقيقة"], h: ["ساعتان", "ساعات", "ساعة"], d: ["يومان", "أيام", "يوماً"],
  wk: ["أسبوعان", "أسابيع", "أسبوعاً"], mo: ["شهران", "أشهر", "شهراً"] };
export function tfLong(tf: string): string {
  const p = parseTf(tf);
  if (!p) return tf;
  const u = TF_UNITS.find(x => x[0] === p.unit)!, w = TF_WORDS[p.unit];
  return p.n === 1 ? u[1] : p.n === 2 ? w[0] : p.n <= 10 ? `${p.n} ${w[1]}` : `${p.n} ${w[2]}`;
}
export const tfIntraday = (tf: string) => { const p = parseTf(tf); return !!p && (p.unit === "m" || p.unit === "h"); };

/* ── الصياغة ── أرقامٌ لاتينية، وشهورٌ عربية */
const _mon = new Intl.DateTimeFormat("ar-u-nu-latn-ca-gregory", { month: "short", timeZone: "UTC" });
const _two = (n: number) => String(n).padStart(2, "0");
const _date = (t: string | number | { year: number; month: number; day: number }) =>
  typeof t === "number" ? new Date(t * 1000)
    : typeof t === "string" ? new Date(t + "T00:00:00Z")
    : new Date(Date.UTC(t.year, t.month - 1, t.day));

/** علامةُ المحور الزمنيّ: 0 سنة · 1 شهر · 2 يوم · 3 وقت. */
export function tickLabel(t: any, type: number): string {
  const d = _date(t);
  if (type === 0) return String(d.getUTCFullYear());
  if (type === 1) return _mon.format(d);
  if (type === 2) return String(d.getUTCDate());
  return `${_two(d.getUTCHours())}:${_two(d.getUTCMinutes())}`;
}
/** وسمُ خطّ التقاطع: «12 نوفمبر 2026» أو معه الساعة. */
export function crossLabel(t: any): string {
  const d = _date(t);
  const base = `${d.getUTCDate()} ${_mon.format(d)} ${d.getUTCFullYear()}`;
  return typeof t === "number" ? `${base}  ${_two(d.getUTCHours())}:${_two(d.getUTCMinutes())}` : base;
}
export function fmtPrice(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return "—";
  const a = Math.abs(v);
  const dp = a >= 1 || a === 0 ? 2 : a >= 0.01 ? 4 : 6;
  return v.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp });
}
export function fmtVol(v: number | null | undefined): string {
  if (v == null || !isFinite(v) || v <= 0) return "—";
  const u: [number, string][] = [[1e9, "B"], [1e6, "M"], [1e3, "K"]];
  for (const [k, s] of u) if (v >= k) return (v / k).toFixed(v / k >= 100 ? 0 : v / k >= 10 ? 1 : 2) + s;
  return String(Math.round(v));
}
