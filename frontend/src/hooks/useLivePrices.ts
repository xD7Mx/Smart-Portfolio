/* أسعارٌ تتحرّك بالدفع لا بالسؤال — صفرُ تأخيرٍ من جهة التطبيق (D290).
 *
 * طلب المالك أرقاماً تتحرّك «مثل التطبيق البنكيّ بدون تأخيرٍ نهائياً».
 * والسؤالُ الدوريُّ فيه تأخيرٌ **بنيويّ**: الرقمُ يصل الخادمَ في لحظةٍ
 * وتسأل الشاشةُ بعدها. فقُلب الاتّجاه: `EventSource` يفتح مجرًى واحداً،
 * والخادمُ يدفع كلَّ سعرٍ يتغيّر لحظةَ وصوله.
 *
 * ## لماذا مخزنٌ خارجيٌّ لا حالةُ مكوِّن
 * الدفعةُ قد تحمل مئتَي رمزٍ في الثانية. ولو كانت حالةَ مكوِّنٍ أعلى
 * لأعادت رسمَ الشجرة كلِّها كلَّ ثانية. فالمخزنُ خارجيٌّ
 * (`useSyncExternalStore`) **مقسَّمٌ بالرمز**: لا يُعاد رسمُ إلا الرقمِ
 * الذي تغيّر فعلاً — وهذا هو سرُّ سلاسة تطبيقات البنوك.
 *
 * ## ومجرًى واحدٌ للتطبيق كلِّه
 * الاشتراكُ مرجعيٌّ (‏refcount): أوّلُ مكوِّنٍ يفتح المجرى، وآخرُ من يغادر
 * يُغلقه. فلا مجرًى لكلّ بطاقةٍ ولا اتّصالاتٌ متراكمة.
 *
 * ## والانقطاعُ يُعالَج
 * إعادةُ وصلٍ بتراجعٍ متزايد (ثانيةً ثمّ أكثرَ حتى ثلاثين)، وعندما تكون
 * الصفحةُ مخفيّةً يُغلَق المجرى — لا بثٌّ لشاشةٍ لا يراها أحد. ومن انقطع
 * عنه رجع إلى السؤال الدوريّ: **الرقمُ نفسُه متأخّراً قليلاً، لا رقمٌ آخر**.
 */
import { useSyncExternalStore } from "react";

type Quote = { p: number; c: number | null; at: number };

const quotes = new Map<string, Quote>();
const listeners = new Map<string, Set<() => void>>();
const globalListeners = new Set<() => void>();

let es: EventSource | null = null;
let refs = 0;
let retry = 0;
let retryTimer: number | null = null;
let connected = false;

/* ══ «موصولٌ» ليس «يُوصِل» ══ (D299)
   قال المالك: «مكتوبٌ جلسةٌ مباشرة والرقمُ ثابتٌ لا يتغيّر». وهذا بعينه
   ما تفعله شيفرتُنا: الشاشاتُ كانت تُبطئ سؤالَها الدوريَّ إلى دقيقةٍ
   بمجرّد **نجاح الاتّصال**، لا بوصول دفعة. فإن سكت الخادمُ لأيّ سبب
   (تجديدٌ يرفضه المصدر · مضخّةٌ متعثّرة) تجمّد كلُّ رقمٍ في التطبيق —
   والسِترةُ التي بُنيت للانقطاع لا تعمل، لأن المجرى «موصولٌ» وصامت.
   فالحكمُ صار بالوصول لا بالوصل: دفعةٌ خلال عشرين ثانيةً ⇒ الدفعُ حيّ،
   وإلّا رجعت الشاشةُ إلى سؤالها السريع وحدَها. */
const DELIVER_MS = 20_000;
let lastPayloadAt = 0;
let watchdog: number | null = null;
let index: [number, number | null] | null = null;

function delivering(): boolean {
  return connected && lastPayloadAt > 0 && Date.now() - lastPayloadAt < DELIVER_MS;
}

function emit(symbol: string): void {
  listeners.get(symbol)?.forEach(f => f());
}

function emitAll(): void {
  globalListeners.forEach(f => f());
}

function put(sym: string, p: number, c: number | null): boolean {
  const prev = quotes.get(sym);
  if (prev && prev.p === p && prev.c === c) return false;
  quotes.set(sym, { p, c, at: Date.now() });
  emit(sym);                         // الرمزُ الذي تغيّر وحدَه يُعاد رسمُه
  return true;
}

/* ══ توزيعُ الدفعة على الثواني — حركةٌ بأرقامٍ حقيقيةٍ لا مختلَقة ══
   (بأمر المالك · D328)

   قال: «اجمع تغيّراتِ الأسعار فترةً ثمّ اعرضها كأنها تتحرّك كلَّ ثانية».
   ونصفُ الفكرة مرفوضٌ ونصفُها مبنيّ:

   **المرفوض** حسابُ أرقامٍ وسيطة. لو صار السهمُ من ‎25.64 إلى ‎25.68
   فعرضُ ‎25.65 و‎25.66 بينهما **أسعارٌ لم تُتداول قطّ** — وقد يُشترى
   عليها. وذلك اختلاقٌ يخالف الخطَّ الأحمر، فلا يُفعل.

   **والمبنيّ** أنّ الدفعةَ الواصلةَ تحمل عشراتِ الرموز، كلُّها **أسعارٌ
   حقيقيةٌ نشرها المصدر**. فبدل أن تقع كلُّها في لحظةٍ ثمّ تسكن الشاشةُ
   خمسَ عشرةَ ثانية، تُعرَض على شرائحَ متتابعةٍ كلَّ رُبع ثانية: فالشاشةُ
   تتحرّك حقاً، وكلُّ رقمٍ فيها منشورٌ لا محسوب.

   وثلاثةُ قيودٍ تمنعه أن يصير تجميلاً ضارّاً:
     · **السهمُ المفتوحُ يُعرض فوراً** (اشتراكٌ بأولوية) — التوزيعُ
       للشريط والقوائم لا لمن تنظر إليه.
     · **وأحدثُ قيمةٍ تطرد أقدمَ منها** في الانتظار: لا يُعرض قديمٌ بعد
       جديدٍ أبداً (الانتظارُ خريطةٌ بالرمز لا طابورُ أحداث).
     · **وسقفُ التأخير الفاصلُ المقيسُ نفسُه** (انظر D329 أدناه)، وما
       بقي يُفرَغ فوراً عند خفاء الصفحة — لا رقمٌ يُحتجَز. */
/* ══ والمدّةُ تُقاس لا تُفترَض ══ (بأمر المالك · D329)
   قال: «الحركةَ المتّصلةَ أريدها بالثواني تتغيّر». وأربعُ ثوانٍ ثابتةٌ
   لا تُحقّقها: دفعةٌ كلَّ خمسٍ تُفرَغ في أربعٍ فتسكن الشاشةُ ثانيةً، ودفعةٌ
   كلَّ خمسَ عشرةَ تُفرَغ في أربعٍ فتسكن إحدى عشرة. فالنافذةُ صارت
   **قياسَ الفاصل بين دفعتين** (متوسّطٌ متحرّكٌ للفواصل الواصلة)،
   فيُوزَّع ما وصل على المدّة التي تُتوقَّع حتى الدفعة التالية: حركةٌ في
   كلّ ثانيةٍ بلا فراغ، وبلا تأخيرٍ يزيد على الفاصل نفسِه. والحدّان
   يمنعان الشططَ: لا أقلَّ من ثانيةٍ ونصفٍ ولا أكثرَ من عشرين ثانية. */
const REVEAL_TICK = 250;             // مل.ث بين شريحةٍ وأخرى
const WIN_MIN = 1_500;
const WIN_MAX = 20_000;
let arriveAt = 0;                    // زمنُ وصول آخرِ دفعة
let gapAvg = 5_000;                  // متوسّطُ الفاصل المقيس بين دفعتين
let deadline = 0;                    // الزمنُ الذي يجب أن يفرُغ عنده الانتظار
const pending = new Map<string, [number, number | null]>();
const priority = new Map<string, number>();   // اشتراكاتُ الأولوية بالرمز
let reveal: number | null = null;

function drainAll(): void {
  let any = false;
  for (const [sym, [p, c]] of pending) any = put(sym, p, c) || any;
  pending.clear();
  if (reveal) { window.clearInterval(reveal); reveal = null; }
  if (any) emitAll();
}

function tick(): void {
  if (!pending.size) {
    if (reveal) { window.clearInterval(reveal); reveal = null; }
    return;
  }
  /* حصّةُ الشريحة: ما يُفرِغ الانتظارَ **عند الموعد** لا قبله — فالحركةُ
     تمتدّ إلى الدفعة التالية ولا تتوقّف في منتصف المدّة. */
  const left = Math.max(REVEAL_TICK, deadline - Date.now());
  const slots = Math.max(1, Math.round(left / REVEAL_TICK));
  const take = Math.max(1, Math.ceil(pending.size / slots));
  let n = 0;
  let any = false;
  for (const [sym, [p, c]] of pending) {
    any = put(sym, p, c) || any;
    pending.delete(sym);
    if (++n >= take) break;
  }
  if (any) emitAll();
  if (!pending.size && reveal) { window.clearInterval(reveal); reveal = null; }
}

function apply(q: Record<string, [number, number | null]>): void {
  let now = false;
  // فاصلُ الوصول يُقاس ويُنعَّم (وزنُ الثلث للجديد): مصدرٌ يتباطأ أو
  // يتسارع تتبعه النافذةُ بلا إعدادٍ يدويّ.
  const t = Date.now();
  if (arriveAt) gapAvg = gapAvg * 0.67 + (t - arriveAt) * 0.33;
  arriveAt = t;
  deadline = t + Math.min(WIN_MAX, Math.max(WIN_MIN, gapAvg));

  for (const [sym, v] of Object.entries(q || {})) {
    // فورياً: السهمُ المفتوحُ أمام المستخدم، ورمزٌ لا قيمةَ له بعد
    // (أوّلُ دفعةٍ كاملةٌ لا تُؤخَّر — وإلا بقيت الشاشةُ فارغةً تنتظر).
    if (priority.has(sym) || !quotes.has(sym)) {
      now = put(sym, v[0], v[1]) || now;
      pending.delete(sym);
    } else {
      pending.set(sym, v);           // الأحدثُ يطرد الأقدم
    }
  }
  if (now) emitAll();
  if (pending.size && reveal === null && typeof window !== "undefined") {
    reveal = window.setInterval(tick, REVEAL_TICK);
  }
}

function open(): void {
  if (es || typeof window === "undefined" || !("EventSource" in window)) return;
  try {
    es = new EventSource("/api/v1/market/stream");
  } catch {
    return;
  }
  es.onopen = () => { connected = true; retry = 0; emitAll(); };
  es.onmessage = (ev) => {
    try {
      const d = JSON.parse(ev.data);
      lastPayloadAt = Date.now();        // وصولٌ مقيسٌ لا اتّصالٌ مفترَض
      if (d?.q) apply(d.q);
      if (Array.isArray(d?.i) && typeof d.i[0] === "number") {
        index = [d.i[0], d.i[1] ?? null];
      }
      emitAll();
    } catch { /* دفعةٌ معطوبةٌ تُتجاهل — لا تُسقط المجرى */ }
  };
  es.onerror = () => {
    connected = false;
    emitAll();
    close();
    if (refs > 0) {
      // تراجعٌ متزايدٌ بسقف: لا إغراقٌ لخادمٍ متعثّر.
      const wait = Math.min(1000 * 2 ** retry++, 30_000);
      retryTimer = window.setTimeout(() => { retryTimer = null; open(); }, wait);
    }
  };
}

function close(): void {
  /* ولا يُفرَغ الانتظارُ هنا: `close` تُنادى في كلّ انقطاعٍ عابرٍ وفي
     كلّ هبوطٍ لعدّاد الاشتراك، فإفراغُه هنا كان يُلغي التوزيعَ من أصله
     (قِيس في المتصفّح: `tick` لم يعمل قطّ · D328). والانتظارُ أرقامٌ
     حقيقيةٌ لا تُفقد: مؤقّتُ التوزيع يُكمل عرضَها. والإفراغُ الفوريُّ
     موضعُه خفاءُ الصفحة وحدَه — ثمّ لا شاشةَ تنظر. */
  es?.close();
  es = null;
  connected = false;
  if (retryTimer) { window.clearTimeout(retryTimer); retryTimer = null; }
}

function acquire(): () => void {
  refs += 1;
  if (refs === 1) {
    open();
    document.addEventListener("visibilitychange", onVisibility);
    /* نبضةُ مراقبةٍ خفيفة: انتهاءُ مدّة الوصول حادثةٌ لا يُبلّغ عنها أحد
       — فلو لم تُقَس لبقيت الشاشةُ تظنّ الدفعَ عاملاً بعد سكوته. */
    watchdog = window.setInterval(emitAll, 5_000);
  }
  return () => {
    refs -= 1;
    if (refs <= 0) {
      refs = 0;
      document.removeEventListener("visibilitychange", onVisibility);
      if (watchdog) { window.clearInterval(watchdog); watchdog = null; }
      close();
    }
  };
}

function onVisibility(): void {
  if (document.hidden) { drainAll(); close(); }
  else if (refs > 0) open();
}

/** سعرُ رمزٍ من المجرى — أو `null` إن لم يصل بعد (فيُقرأ سعرُ الاستعلام).
 *
 *  و`now: true` تعني **لا تأخيرَ لهذا الرمز**: صفحةُ السهم المفتوحةُ
 *  تعرضه لحظةَ وصوله ولا يشملها توزيعُ الدفعة (D328). */
export function useLiveQuote(symbol?: string | null,
                             opts?: { now?: boolean }): Quote | null {
  const key = String(symbol || "").replace(".SR", "").trim();
  const wantNow = !!opts?.now;
  return useSyncExternalStore(
    (cb) => {
      if (!key) return () => {};
      const release = acquire();
      let set = listeners.get(key);
      if (!set) { set = new Set(); listeners.set(key, set); }
      set.add(cb);
      if (wantNow) priority.set(key, (priority.get(key) || 0) + 1);
      return () => {
        set!.delete(cb);
        if (wantNow) {
          const n = (priority.get(key) || 1) - 1;
          if (n > 0) priority.set(key, n);
          else priority.delete(key);
        }
        release();
      };
    },
    () => (key ? quotes.get(key) ?? null : null),
    () => null,
  );
}

/** أيُوصِل المجرى فعلاً؟ — لا «أموصولٌ هو». فالسؤالُ الدوريُّ لا يُبطأ
 *  إلا مقابل دفعةٍ وصلت حقاً، ورقمٌ جامدٌ يرجع بالشاشة إلى سؤالها. */
export function useLiveStreamOn(): boolean {
  return useSyncExternalStore(
    (cb) => {
      const release = acquire();
      globalListeners.add(cb);
      return () => { globalListeners.delete(cb); release(); };
    },
    () => delivering(),
    () => false,
  );
}

/** مؤشّرُ تاسي مدفوعاً: [القيمة، النسبة] — أو `null` إن لم يصل بعد. */
export function useLiveIndex(): [number, number | null] | null {
  return useSyncExternalStore(
    (cb) => {
      const release = acquire();
      globalListeners.add(cb);
      return () => { globalListeners.delete(cb); release(); };
    },
    () => index,
    () => null,
  );
}
