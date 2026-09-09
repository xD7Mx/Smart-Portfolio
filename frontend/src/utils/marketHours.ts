/** Tadawul's main trading session: Sunday–Thursday, 10:00–15:00 Riyadh time. */
export function isTasiOpen(now: Date = new Date()): boolean {
  return getMarketStatus(now).status === "open";
}

export type MarketStatus = {
  status: "open" | "closed" | "weekend";
  label: string;
  color: string;
  detail: string;
};

const DAY_MIN = 24 * 60;
const pad = (n: number) => String(n).padStart(2, "0");
const fmtLeft = (mins: number) => {
  const h = Math.floor(mins / 60), m = mins % 60;
  return h > 0 ? `${h} س ${pad(m)} د` : `${m} د`;
};

/** Riyadh-local weekday (0=Sun..6=Sat) + minutes-since-midnight for `now`. */
function riyadhParts(now: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Riyadh", weekday: "short", hour: "numeric", minute: "numeric", hour12: false,
  }).formatToParts(now);
  const get = (t: string) => parts.find(p => p.type === t)?.value;
  const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const weekday = WD.indexOf(get("weekday") || "Sun");
  const hour = Number(get("hour")) % 24;
  const minute = Number(get("minute"));
  return { weekday, minutes: hour * 60 + minute };
}

const OPEN_MIN = 10 * 60;
const CLOSE_MIN = 15 * 60;

export function getMarketStatus(now: Date = new Date()): MarketStatus {
  const { weekday, minutes } = riyadhParts(now);

  if (weekday === 5 || weekday === 6) {
    return { status: "weekend", label: "عطلة نهاية الأسبوع", color: "var(--ink-muted)", detail: "السوق مغلق — لا تداول أيام الجمعة والسبت" };
  }
  if (minutes >= OPEN_MIN && minutes < CLOSE_MIN) {
    return { status: "open", label: "السوق مفتوح", color: "var(--pos-ink)", detail: `يغلق خلال ${fmtLeft(CLOSE_MIN - minutes)}` };
  }
  if (minutes < OPEN_MIN) {
    return { status: "closed", label: "السوق مغلق", color: "var(--neg-ink)", detail: `يفتح خلال ${fmtLeft(OPEN_MIN - minutes)}` };
  }
  let untilOpen = DAY_MIN - minutes + OPEN_MIN;
  let nextDay = (weekday + 1) % 7;
  while (nextDay === 5 || nextDay === 6) { untilOpen += DAY_MIN; nextDay = (nextDay + 1) % 7; }
  return { status: "closed", label: "السوق مغلق", color: "var(--neg-ink)", detail: `يفتح خلال ${fmtLeft(untilOpen)}` };
}

/** Brent (ICE) trades almost around the clock on business days: it runs
 * Sun 20:00 → Fri 22:00 London with a one-hour daily break (~21:00–22:00
 * London). We keep it honest and simple in Riyadh time (London +2/+3):
 * open on weekdays and Sunday evening, closed on the weekend gap. This is a
 * real-schedule approximation, never a fabricated "live" claim. */
export function getBrentStatus(now: Date = new Date()): MarketStatus {
  const { weekday, minutes } = riyadhParts(now);
  // The market's weekend gap: Friday after ~23:00 Riyadh through Sunday ~22:00.
  const friClosed = weekday === 5 && minutes >= 23 * 60;
  const satClosed = weekday === 6;
  const sunClosed = weekday === 0 && minutes < 22 * 60;
  if (friClosed || satClosed || sunClosed) {
    return { status: "weekend", label: "مغلق (عطلة)", color: "var(--ink-muted)", detail: "سوق برنت مغلق خلال عطلة نهاية الأسبوع" };
  }
  // Daily one-hour maintenance break (~00:00–01:00 Riyadh).
  if (minutes >= 0 && minutes < 60) {
    return { status: "closed", label: "توقف مؤقت", color: "var(--warn-ink)", detail: "استراحة يومية قصيرة — يُستأنف بعد قليل" };
  }
  return { status: "open", label: "التداول مفتوح", color: "var(--pos-ink)", detail: "سوق برنت في جلسة تداول نشطة" };
}

/* ══ أطوار السوق الأربعة — المصدر الواحد ══
   كانت هذه الدالّة داخل `LiveClock.tsx` وحدها، فتعرف الساعةُ «قبل
   الافتتاح» و«قبل الإغلاق» ولا تعرفهما نقطةُ حالة السوق — لأنها تقرأ
   `getMarketStatus` أعلاه وهي بطورين لا أربعة. فنُقلت هنا ليقرأ الاثنان
   من موضعٍ واحد، ويبقى `getMarketStatus` لمن يريد الثنائية المبسّطة. */
export type TasiPhase = { key: "pre" | "open" | "preclose" | "closed"; label: string; color: string };

export function tasiPhase(d: Date = new Date()): TasiPhase {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Riyadh", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value || "";
  const WD: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  let hour = parseInt(get("hour"), 10);
  if (hour === 24) hour = 0;
  const mins = hour * 60 + parseInt(get("minute"), 10);
  const wd = WD[get("weekday")] ?? 0;
  const trading = wd >= 0 && wd <= 4;          // الأحد…الخميس
  if (trading && mins >= 9 * 60 + 30 && mins < 10 * 60)
    return { key: "pre", label: "قبل الافتتاح", color: "var(--st-pre)" };
  /* ══ ساعاتُ تداول الحقيقية ══ (رآه المالك: «مغلق» والسوقُ يعمل)
     التداولُ المستمرّ حتى 15:00، ثمّ مزادُ الإغلاق 15:00–15:10، ثمّ
     التداولُ عند سعر الإغلاق حتى 15:20. فكان يقول «قبل الإغلاق» ونصفُ
     ساعةٍ من الجلسة باقية، و«مغلق» وعشرون دقيقةً من المزاد قائمة.
     ونسخةُ الخادم في `settings.py` أُصلحت معها — القاعدةُ في موضعين. */
  if (trading && mins >= 10 * 60 && mins < 15 * 60)
    return { key: "open", label: "السوق مفتوح", color: "var(--st-open)" };
  if (trading && mins >= 15 * 60 && mins < 15 * 60 + 20)
    return { key: "preclose", label: "قبل الإغلاق", color: "var(--st-preclose)" };
  return { key: "closed", label: "السوق مغلق", color: "var(--st-idle)" };
}
