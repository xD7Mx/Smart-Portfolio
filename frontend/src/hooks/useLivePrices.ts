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

function apply(q: Record<string, [number, number | null]>): void {
  const now = Date.now();
  for (const [sym, [p, c]] of Object.entries(q || {})) {
    const prev = quotes.get(sym);
    if (prev && prev.p === p && prev.c === c) continue;
    quotes.set(sym, { p, c, at: now });
    emit(sym);                       // الرمزُ الذي تغيّر وحدَه يُعاد رسمُه
  }
  emitAll();
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
  if (document.hidden) close();
  else if (refs > 0) open();
}

/** سعرُ رمزٍ من المجرى — أو `null` إن لم يصل بعد (فيُقرأ سعرُ الاستعلام). */
export function useLiveQuote(symbol?: string | null): Quote | null {
  const key = String(symbol || "").replace(".SR", "").trim();
  return useSyncExternalStore(
    (cb) => {
      if (!key) return () => {};
      const release = acquire();
      let set = listeners.get(key);
      if (!set) { set = new Set(); listeners.set(key, set); }
      set.add(cb);
      return () => { set!.delete(cb); release(); };
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
