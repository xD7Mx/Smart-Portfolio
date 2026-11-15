/* بياناتُ الرسم البيانيّ — دوالُّ خالصةٌ يفحصها الحارسُ بنفسها (‏scripts/audit/pro_chart_d736.mjs).
   ══ ‏D736 (المالك 2026-11-15): «رسمٌ احترافيٌّ يغنيني عن تريدنق فيو… شموعٌ حقيقية… وخيارُ تخصيصٍ في الأطر» ══
   الخادمُ ينظّف الشموعَ (‏D735)، وهنا خطُّ الدفاع الثاني: المكتبةُ ترفض سلسلةً فيها زمنٌ مكرَّرٌ أو غيرُ مرتَّب فتُعرض فارغة —
   فلا تُسلَّم إلّا مرتَّبةً بلا تكرارٍ ولا شمعةٍ مختلّة. والوقتُ دون اليوم بتوقيت الرياض كما يكتبه الخادم: يُمرَّر «ساعةَ
   حائطٍ» فيقرأ المحورُ 10:00 لافتتاح الرياض (كان يُحوَّل إلى التوقيت العالميّ فيقرأ 07:00). */
export type RawBar = { date: string; open: number; high: number; low: number; close: number; volume?: number };
export type CBar = RawBar & { time: string | number };

/** «2026-11-12» يومُ جلسةٍ كما هو (كتريدنق فيو: الشمعةُ اليوميةُ لا تتبع منطقةً زمنية)؛ و«2026-11-12 10:00» — ختمُ الخادم
    بساعة الرياض (‏UTC+3 ثابتٌ بلا توقيتٍ صيفيّ) — ثوانٍ بالتوقيت العالميّ الحقيقيّ (‏D739). والعرضُ بأيّ منطقةٍ يختارها المالك
    (‏displayTimes). */
export function barTime(date: string): string | number {
  const d = String(date || "");
  if (d.length <= 10) return d;
  return Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10), +d.slice(11, 13), +d.slice(14, 16)) / 1000 - 10800;
}

/* ══ المناطقُ الزمنية كتريدنق فيو (‏D739 · المالك 2026-11-15: «توقيتٌ موحّدٌ مثل تريدنق فيو… أغيّره −3 −2 على توقيت غرينتش») ══
   «توقيتُ البورصة» افتراضاً (كتريدنق فيو)، و«UTC»، ومدنٌ تغطّي الفروقَ من −10 إلى +13 — وفرقُ كلٍّ يُحسب لحظتَه (الصيفيُّ والشتويّ). */
export const TZ_LIST: [string, string][] = [
  ["Pacific/Honolulu", "هونولولو"], ["America/Anchorage", "أنكوريج"], ["America/Los_Angeles", "لوس أنجلوس"], ["America/Denver", "دنفر"],
  ["America/Chicago", "شيكاغو"], ["America/New_York", "نيويورك"], ["America/Halifax", "هاليفاكس"], ["America/Sao_Paulo", "ساو باولو"],
  ["Atlantic/South_Georgia", "جورجيا الجنوبية"], ["Atlantic/Azores", "الأزور"], ["Europe/London", "لندن"], ["Europe/Berlin", "برلين"],
  ["Africa/Cairo", "القاهرة"], ["Asia/Riyadh", "الرياض"], ["Asia/Dubai", "دبي"], ["Asia/Karachi", "كراتشي"], ["Asia/Kolkata", "كولكاتا"],
  ["Asia/Dhaka", "دكا"], ["Asia/Bangkok", "بانكوك"], ["Asia/Singapore", "سنغافورة"], ["Asia/Tokyo", "طوكيو"], ["Australia/Sydney", "سيدني"],
  ["Pacific/Auckland", "أوكلاند"]];

/** منطقةُ البورصة لرمزٍ — كما يعرضها تريدنق فيو افتراضاً. */
export function exchangeTz(symbol: string): string {
  const s = String(symbol || "").toUpperCase();
  if (/^\d{4}(\.SR)?$/.test(s) || s.endsWith(".SR") || /TASI/.test(s)) return "Asia/Riyadh";
  if (/-(USD|USDT|EUR|BTC|ETH)$/.test(s)) return "UTC";
  if (/^BZ=F$/.test(s) || s.endsWith(".L") || s === "^FTSE") return "Europe/London";
  if (s.endsWith(".DE") || s === "^GDAXI") return "Europe/Berlin";
  if (s.endsWith(".T") || s === "^N225") return "Asia/Tokyo";
  if (s.endsWith("=X")) return "Europe/London";
  return "America/New_York";
}

const _fmts = new Map<string, Intl.DateTimeFormat>();
/** فرقُ المنطقة عن التوقيت العالميّ بالدقائق في لحظةٍ بعينها (الصيفيُّ يُحسب). */
export function tzOffsetMin(tz: string, utcSec: number): number {
  if (!tz || tz === "UTC") return 0;
  let f = _fmts.get(tz);
  if (!f) {
    try { f = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
    catch { return 0; }
    _fmts.set(tz, f);
  }
  const p: Record<string, number> = {};
  for (const x of f.formatToParts(new Date(utcSec * 1000))) if (x.type !== "literal") p[x.type] = +x.value;
  const wall = Date.UTC(p.year, p.month - 1, p.day, p.hour % 24, p.minute) / 1000;
  return Math.round((wall - Math.floor(utcSec / 60) * 60) / 60);
}
export function fmtOffset(min: number): string {
  if (!min) return "UTC";
  const a = Math.abs(min), h = Math.floor(a / 60), m = a % 60;
  return `UTC${min > 0 ? "+" : "−"}${h}${m ? ":" + String(m).padStart(2, "0") : ""}`;
}

/** أوقاتُ العرض: الشمعةُ دون اليوم تُزاح بفرق المنطقة في لحظتها فيقرأ المحورُ ساعتَها هناك، واليوميةُ كما هي. وتبقى متزايدةً
    تماماً — ساعةُ الرجوع عن الصيفيّ تتكرّر في الساعة الحائطية والمكتبةُ ترفض التكرار. */
export function displayTimes(bars: { time: string | number }[], tz: string): (string | number)[] {
  const out: (string | number)[] = new Array(bars.length);
  let prev = -Infinity, cacheH = NaN, cacheOff = 0;
  for (let i = 0; i < bars.length; i++) {
    const t = bars[i].time;
    if (typeof t !== "number") { out[i] = t; continue; }
    const h = Math.floor(t / 3600);
    if (h !== cacheH) { cacheH = h; cacheOff = tzOffsetMin(tz, h * 3600 + 1800); }
    let d = t + cacheOff * 60;
    if (d <= prev) d = prev + 1;
    out[i] = prev = d;
  }
  return out;
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
