import React, { useEffect, useMemo, useRef, useState } from "react";
import { settingsApi } from "../../services/api";
import { useAppStore } from "../../store/appStore";

/**
 * الساعة الرسمية للتطبيق — توقيت مكة (Asia/Riyadh). مرسّخة على **ساعة الخادم**:
 * تُزامن مع /settings/server-time عند الإقلاع وكل ٥ دقائق، فتطابق تمامًا التوقيت
 * الذي يعتمده الخادم في لقطات المحفظة والتدوير اليومي وأطوار السوق — وتبقى صحيحة
 * حتى لو كانت ساعة جهاز المستخدم مغلوطة. بين المزامنات تُحسب محليًّا بإضافة فارق
 * الخادم (drift). عند تعذّر الخادم تسقط بأمان إلى توقيت مكة من Intl على الجهاز.
 *
 * التاريخ يُعرض ميلاديًّا وهجريًّا (طابع رسمي سعودي). الأرقام عربية عبر ar-SA.
 */

const TZ = "Asia/Riyadh";
const WD: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

/** لحظة مكة كمكوّنات (يوم الأسبوع 0=الأحد + دقائق اليوم) — لحساب حالة السوق. */
function meccaMoment(d: Date): { wd: number; mins: number; secs: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value || "";
  let hour = parseInt(get("hour"), 10);
  if (hour === 24) hour = 0;   // بعض المحرّكات تُرجع 24 عند منتصف الليل
  const mins = hour * 60 + parseInt(get("minute"), 10);
  return { wd: WD[get("weekday")] ?? 0, mins, secs: mins * 60 + parseInt(get("second"), 10) };
}

const OPEN_MIN = 10 * 60;          // ١٠:٠٠ افتتاح التداول
const CLOSE_MIN = 15 * 60;         // ١٥:٠٠ الإغلاق
const DAY_SECS = 24 * 3600;

/**
 * العدّاد: كم بقي على الافتتاح، فإذا افتُتح انقلب إلى كم بقي على الإغلاق.
 * محسوب بتوقيت مكة من نفس لحظة الساعة (المرسّخة بالخادم)، لا من ساعة الجهاز.
 * أيام التداول الأحد–الخميس، فبعد إغلاق الخميس يقفز العدّاد إلى أحد القادم.
 */
function countdown(d: Date): { label: string; text: string } | null {
  const { wd, secs } = meccaMoment(d);
  const trading = wd >= 0 && wd <= 4;
  if (trading && secs >= OPEN_MIN * 60 && secs < CLOSE_MIN * 60) {
    return { label: "يُغلق بعد", text: hms(CLOSE_MIN * 60 - secs) };
  }
  // إلى الافتتاح القادم: اليوم إن كان يوم تداول ولمّا يفتح بعد، وإلا أوّل يوم تداول تالٍ.
  let remaining = OPEN_MIN * 60 - secs;
  let day = wd;
  if (!trading || remaining <= 0) {
    remaining += DAY_SECS;
    day = (day + 1) % 7;
    while (day > 4) { remaining += DAY_SECS; day = (day + 1) % 7; }
  }
  return { label: "يفتح بعد", text: hms(remaining) };
}

/** صياغة مدّة بالساعات/الدقائق/الثواني — أرقام لاتينية، بلا حشو. */
function hms(total: number): string {
  const s = Math.max(0, Math.floor(total));
  const d = Math.floor(s / DAY_SECS);
  const h = Math.floor((s % DAY_SECS) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d} ي ${h} س`;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

type Status = { key: string; label: string; color: string };

/* حالةُ السوق بأطوارها الأربعة صارت في `utils/marketHours` — موضعٌ واحد.
   كانت هنا، وفي `marketHours` نسخةٌ ثانية بطورين (مفتوح/مغلق) تقرؤها
   نقطةُ حالة السوق. فكانت الساعة تعرف «قبل الافتتاح» والنقطةُ لا تعرفه
   ولا تستطيع — لا لأنها لا تعرضه بل لأن مصدرها لا يحمله. وتعريفان
   لمفهومٍ واحد هو عين ما تشكو منه اللجنة في الرموز والحقول. */
import { tasiPhase } from "../../utils/marketHours";
const marketStatus = tasiPhase;

export default function LiveClock() {
  const showClock = useAppStore((s) => s.showClock);
  const showMarketStatus = useAppStore((s) => s.showMarketStatus);
  const clockSeconds = useAppStore((s) => s.clockSeconds);
  const clockHour12 = useAppStore((s) => s.clockHour12);
  const clockDate = useAppStore((s) => s.clockDate);
  // فارق ساعة الخادم عن ساعة الجهاز (ms): now الرسمي = Date.now() + drift.
  const [drift, setDrift] = useState(0);
  const [open, setOpen] = useState(false);   // نافذة التفاصيل المنبثقة
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [serverStatus, setServerStatus] = useState<string | null>(null);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    let alive = true;
    const sync = async () => {
      try {
        const t0 = Date.now();
        const r = await settingsApi.serverTime();
        const rtt = (Date.now() - t0) / 2;            // نصف زمن الرحلة تقريبًا
        const d = r.data?.data;
        if (alive && d?.epoch_ms) {
          setDrift(d.epoch_ms + rtt - Date.now());     // تعويض زمن الشبكة
          setServerStatus(d.market_status ?? null);
        }
      } catch { /* الخادم غير متاح → نبقى على توقيت الجهاز (fallback) */ }
    };
    sync();
    const s = setInterval(sync, 5 * 60 * 1000);        // إعادة ترسيخ كل ٥ دقائق
    return () => { alive = false; clearInterval(s); };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date(Date.now() + drift)), 1000);
    return () => clearInterval(t);
  }, [drift]);

  // مُنسّق الوقت يتبع تفضيلات المستخدم (١٢/٢٤ ساعة · إظهار الثواني).
  const fmt = useMemo(() => {
    const timeOpts: Intl.DateTimeFormatOptions = {
      timeZone: TZ, hour: clockHour12 ? "numeric" : "2-digit", minute: "2-digit", hour12: clockHour12,
    };
    if (clockSeconds) timeOpts.second = "2-digit";
    // nu-latn = أرقام لاتينية (العُرف المعتمد في المشروع كلّه) مع أسماء عربية.
    return {
      time: new Intl.DateTimeFormat("ar-SA-u-nu-latn", timeOpts),
      greg: new Intl.DateTimeFormat("ar-u-ca-gregory-nu-latn", {
        timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric",
      }),
      hijri: new Intl.DateTimeFormat("ar-SA-u-ca-islamic-umalqura-nu-latn", {
        timeZone: TZ, day: "numeric", month: "long", year: "numeric",
      }),
    };
  }, [clockHour12, clockSeconds]);

  // حالة السوق: من الخادم (المرجع) متى توفّرت، وإلا حساب محلّي بتوقيت مكة.
  const STATUS_MAP: Record<string, Status> = {
    open: { key: "open", label: "السوق مفتوح", color: "var(--st-open)" },
    pre: { key: "pre", label: "قبل الافتتاح", color: "var(--st-pre)" },
    preclose: { key: "preclose", label: "قبل الإغلاق", color: "var(--st-preclose)" },
    closed: { key: "closed", label: "السوق مغلق", color: "var(--st-idle)" },
  };
  const st = (serverStatus && STATUS_MAP[serverStatus]) || marketStatus(now);
  const cd = countdown(now);
  let hijri = "";
  try { hijri = fmt.hijri.format(now).replace(/\s*هـ?$/, "") + " هـ"; } catch { /* بعض المتصفحات بلا تقويم أم القرى */ }

  // الضغط يُظهر النافذة المنبثقة ثم تختفي تلقائيًّا بعد ٣ ثوانٍ (بانميشن خفيف).
  const flash = () => {
    setOpen(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setOpen(false), 3000);
  };
  useEffect(() => () => { if (hideTimer.current) clearTimeout(hideTimer.current); }, []);

  /* المؤشّر المجاور للساعة لا يظهر إلا حين يحمل خبراً.
     العلّة التي يعالجها: مؤشّرٌ دائم يشغل حيّزاً بجانب أهمّ عنصر في الشريط
     بينما لا يقول جديداً في معظم الوقت (السوق مغلق أغلب اليوم وكل نهاية
     الأسبوع، والمفتوح حالة مستقرّة لا تحتاج تذكيراً) — فيتحوّل من إشارة إلى
     زينة، والزينة الدائمة بجانب رقم متغيّر تُتعب البصر.

     القاعدة: يظهر في الطورين الانتقاليّين فقط — «قبل الافتتاح» و«قبل الإغلاق».
     فيصير ظهوره نفسه هو المعلومة: شيءٌ على وشك أن يحدث. وفي «مفتوح» و«مغلق»
     تبقى الساعة وحدها نظيفة. الحالة الكاملة والعدّاد في نافذة الساعة دائماً،
     فلا معلومة تُفقد — يُلغى التذكير الدائم بها فقط.

     السويتش في الإعدادات يبقى قادراً على إطفائه كلّياً. */
  const ALERT_PHASES = ["pre", "preclose"];
  const statusInline = showMarketStatus && ALERT_PHASES.includes(st.key);
  const hasInline = showClock || statusInline;
  if (!hasInline) return null;

  /**
   * مؤشّر الحالة داخل **نافذة الساعة** — النموذج ٢ «الحلقة» (لغة البنوك).
   * أمّا في الشريط فلا نقطة إطلاقاً: الأرقام نفسها تتوهّج (.clock-glow). بحجم ثابت في كل
   * الأطوار فلا يقفز الصفّ، ويمين الساعة تماماً على الجوال والكمبيوتر معاً:
   *   مفتوح       → حلقة ممتلئة خضراء بهالة خفيفة (نشِط)
   *   قبل الافتتاح → حلقة مفرغة كهرمانية وامضة (على وشك)
   *   قبل الإغلاق  → حلقة مفرغة زرقاء ثابتة
   *   مغلق        → حلقة مفرغة رمادية بشرطة تعبرها (ساكن)
   *
   * الأطوار الأربعة كلّها تُرسم في **نافذة الساعة**؛ أمّا في الشريط فلا يظهر
   * منها إلا الطوران الانتقاليّان (انظر ALERT_PHASES أعلاه).
   *
   * الفكرة الحاكمة: الفرق بين المفرغ والممتلئ يُقرأ **بالشكل** لا باللون، فيصمد
   * مع عمى الألوان ومع الشاشة تحت الشمس — وهذا ما يميّزه عن النقطة المصمتة.
   * سماكة الحدّ نسبية من القطر كي تبقى الفجوة الداخلية مرئية لو صُغّر لاحقاً.
   * لا نصّ بجانب الساعة إطلاقاً — التفاصيل مكانها النافذة المنبثقة.
   */
  const Dot = ({ size = 5 }: { size?: number }) => {
    const ring = Math.max(1, size * 0.22);             // سماكة الحلقة (نسبية، بحدٍّ أدنى يُبقي الفجوة مرئية)
    const filled = st.key === "open";
    return (
      <span className="relative flex items-center justify-center shrink-0" style={{ height: size, width: size }}>
        {filled && (
          <span className="absolute inline-flex h-full w-full rounded-full opacity-55 animate-ping" style={{ background: st.color }} />
        )}
        <span className={"relative inline-flex rounded-full " + (st.key === "pre" ? "st-blink" : "")}
          style={{
            height: size, width: size, boxSizing: "border-box",
            border: `${ring}px solid ${st.color}`,
            background: filled ? st.color : "transparent",
            boxShadow: filled ? `0 0 0 2px color-mix(in srgb, ${st.color} 22%, transparent)` : undefined,
          }} />
        {st.key === "closed" && (
          /* الشرطة تعبر الحلقة بلونها نفسه — تُقرأ كعلامة «متوقّف» لا كخدش. */
          <span className="absolute rounded-full"
            style={{ width: Math.round(size * 0.72), height: ring, background: st.color }} />
        )}
      </span>
    );
  };

  // ساعة سادة موحّدة (جوال ومنتصف الشريط · كمبيوتر ويسارًا). التفاصيل نافذة
  // منبثقة صغيرة تظهر بلطف عند الضغط وتختفي بعد ٣ ثوانٍ — لا قائمة منسدلة.
  const showGreg = clockDate === "greg" || clockDate === "both";
  const showHijri = (clockDate === "hijri" || clockDate === "both") && !!hijri;

  return (
    <div className="live-clock relative flex items-center shrink-0 select-none">
      {/* الساعة في مكانها تماماً (سطر أول)، وحالة السوق **أسفلها** كحاشية
          صغيرة لا تُزحزح الساعة بأي شكل: العمود مركزي والحالة absolute تحت
          الساعة فلا تدخل في حساب ارتفاع الصفّ ولا تغيّر موضعها. */}
      <button onClick={flash} title={`${fmt.greg.format(now)} — ${st.label}`}
        aria-label={`التوقيت — ${st.label}`}
        className="relative flex items-center gap-[9px] px-1 py-1 active:scale-95 transition-transform">
        {/* المؤشّر أوّل عنصر في ترتيب DOM ⇒ يمين الساعة بصريًّا في RTL،
            و`items-center` على الصفّ يجعله في منتصف سطر الساعة تماماً.
            لا يُرسم إلا في الطورين الانتقاليّين. */}
        {showClock && (
          <span
            className={"font-bold text-[var(--ink)] tabular-nums text-base sm:text-lg tracking-tight leading-none"
              + (statusInline ? " clock-glow" : "")}
            style={statusInline ? ({ "--gc": st.color } as React.CSSProperties) : undefined}>
            {fmt.time.format(now)}
          </span>
        )}
      </button>

      {/* نافذة منبثقة: تحت الساعة، مركزيّة على الجوال ومحاذاة للطرف على الكمبيوتر.
          انتقال خفيف للظهور/الاختفاء (opacity + إزاحة صغيرة). */}
      <div
        className={
          "clock-pop absolute top-full mt-2 z-50 w-60 rounded-2xl border border-[var(--hairline)] bg-[var(--raised)] shadow-xl p-3.5 " +
          "left-1/2 -translate-x-1/2 " +   /* مركزيّة تحت الساعة في المنتصف */
          "transition-all duration-300 ease-out " +
          (open ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 -translate-y-1 pointer-events-none")
        }
      >
        {/* حالة السوق داخل النافذة **دائمة** ولا يحكمها سويتش الإعدادات: النافذة
            لا تُفتح إلا بقصدٍ من المستخدم، فإخفاء المعلومة فيها إخفاءٌ بلا فائدة.
            دور السويتش صار مقصوراً على المؤشّر المجاور للساعة في الشريط. */}
        <div className="flex items-center justify-between mb-2.5">
          <span className="flex items-center gap-1.5">
            <Dot size={7} />
            <span className="text-xs font-bold" style={{ color: st.color }}>{st.label}</span>
          </span>
          {showClock && <span className="font-bold text-[var(--ink)] tabular-nums text-lg">{fmt.time.format(now)}</span>}
        </div>
        {/* العدّاد: سطر واحد هادئ تحت الحالة مباشرةً — «يفتح بعد» قبل الجلسة،
            ينقلب تلقائيًّا إلى «يُغلق بعد» فور الافتتاح. الأرقام tabular فلا
            يرتجف عرض السطر مع كل ثانية. لم نُغيّر شيئاً آخر في النافذة. */}
        {cd && (
          <div className="clock-cd flex items-center justify-between rounded-xl px-2.5 py-1.5 mb-2.5">
            <span className="text-[11px] font-medium text-[var(--ink-muted)]">{cd.label}</span>
            <span className="text-[13px] font-bold tabular-nums" style={{ color: st.color }}>{cd.text}</span>
          </div>
        )}
        {(showGreg || showHijri) && <div className="h-px bg-[var(--surface)] mb-2.5" />}
        {(showGreg || showHijri) && (
          <div className="space-y-1.5 text-right">
            {showGreg && <p className="text-[13px] text-[var(--ink)] font-medium">{fmt.greg.format(now)}</p>}
            {showHijri && <p className="text-xs text-[var(--ink-muted)]">{hijri}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
