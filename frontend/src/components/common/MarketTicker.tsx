import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi, settingsApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
// أيقونة اللسان هي أيقونة شريط الأخبار نفسها (`Radio` — موجاتُ بثّ). كانت
// `Newspaper` فبدا في التطبيق رمزان لشيءٍ واحد، والمالك يقرؤهما قسمين.
import { Radio } from "lucide-react";
import TadawulLogo from "./TadawulLogo";
import TrendArrow from "./TrendArrow";

/**
 * شريط حركة السوق — تحت شريط الأخبار مباشرةً.
 *
 * اللسان الثابت ليس كلمةً بل **مؤشّر تاسي نفسه**: قيمته الحيّة وتحتها نسبة
 * تغيّره، ملوّنةً بحالته. فالمكان الذي كان يحمل عنواناً يحمل الآن معلومة.
 *
 * وما يمرّ بجانبه شركات السوق: الاسم · السعر · مثلّثٌ يقول الاتجاه · والنسبة
 * ملوّنة. أخضر صعوداً، أحمر نزولاً، أصفر تعادلاً.
 *
 * **لا يتوقّف بعد الإغلاق** بأمر المالك: يستمرّ بأسعار آخر جلسة. ولئلّا
 * يُقرأ رقمُ أمسٍ كأنه سعر اللحظة، يظهر وسم «إغلاق» في اللسان نفسه — الحركة
 * تبقى، والصدق يبقى معها.
 */
export default function MarketTicker() {
  const isOwner = useAuthStore(s => s.isOwner);

  const { data: overview } = useQuery({
    queryKey: ["market-overview"],
    queryFn: () => marketApi.overview().then(r => r.data.data),
    refetchInterval: 5 * 60 * 1000,
    enabled: isOwner,
  });
  const { data: news = [] } = useQuery({
    queryKey: ["market-news", "ar"],
    queryFn: () => marketApi.news("ar").then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    refetchInterval: 5 * 60 * 1000,
    enabled: isOwner,
  });
  const { data: movers } = useQuery({
    queryKey: ["market-movers"],
    queryFn: () => marketApi.movers().then(r => r.data.data),
    refetchInterval: 5 * 60 * 1000,
    enabled: isOwner,
  });

  /* لسانٌ واحد يتبدّل بالضغط: إمّا حركة السوق وإمّا الأخبار — لا خلطَ
     بينهما في مسارٍ واحد ولا لسانان. الاختيار يُحفظ فيبقى بين الزيارات. */
  const [mode, setMode] = useState<"market" | "news">(() =>
    (localStorage.getItem("ticker:mode") as any) === "news" ? "news" : "market");
  const swap = () => setMode(m => {
    const next = m === "market" ? "news" : "market";
    localStorage.setItem("ticker:mode", next);
    return next;
  });

  /* ══ طورُ الجلسة من الخادم ══
     الخادم يحسب الأطوار الأربعة بتوقيت مكة (`/settings/server-time`):
     `pre` · `open` · `preclose` · `closed`. وكان اللسان يقنع بثنائيةٍ
     مشتقّة من قِدَم البيانات — فلا يفرّق بين «مغلق» و«قبل الافتتاح»،
     وهما حالتان يتصرّف المالك في كلٍّ منهما تصرّفاً مختلفاً. ولا يُحسب
     الطور في المتصفّح: ساعة الجهاز قد تكون مغلوطة، والخادم مرجعٌ واحد. */
  const { data: srv } = useQuery({
    queryKey: ["server-time"],
    queryFn: () => settingsApi.serverTime().then(r => r.data.data),
    refetchInterval: 60 * 1000,
    enabled: isOwner,
  });

  const tasi = overview?.tasi;
  /* بياناتٌ قديمة تعني جلسةً منتهية مهما قال التقويم — والصدق مقدَّم. */
  const stale = !!movers?._stale_since;
  const phase: string = stale ? "closed" : (srv?.market_status || "closed");
  const closed = phase === "closed";

  /* الترتيب: الأكثر حركةً أولاً، صعوداً ونزولاً بالتناوب — الشريط يلفت النظر
     إلى ما تحرّك، لا يفهرس السوق أبجدياً. */
  const rows = useMemo(() => {
    if (mode === "news") {
      return (news || [])
        .filter((n: any) => n?.headline && (n.trusted || n.company))
        .slice(0, 12)
        .map((n: any) => ({ kind: "news", headline: n.headline, url: n.url, source: n.source }));
    }
    /* يكفي اسمٌ أو رمز — والسعر اختياريّ. اشتراطُ الرمز كان يُسقط الصفوف
       التي تحمل الاسم وحده فيظهر الشريط فارغاً بلا سبب ظاهر. */
    const ok = (r: any) => r && (r.name || r.symbol) && r.change_pct != null;
    const up = (movers?.gainers || []).filter(ok);
    const dn = (movers?.losers || []).filter(ok);
    const out: any[] = [];
    for (let i = 0; i < Math.max(up.length, dn.length); i++) {
      if (up[i]) out.push({ kind: "quote", ...up[i] });
      if (dn[i]) out.push({ kind: "quote", ...dn[i] });
    }
    return out;
  }, [movers, news, mode]);

  /* المدّة تتناسب مع طول المحتوى فتبقى السرعة ثابتةً مقروءة مهما زاد العدد
     — نفس مبدأ شريط الأخبار. */
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [duration, setDuration] = useState(60);
  useEffect(() => {
    const el = trackRef.current;
    if (!el || !rows.length) return;
    const w = el.scrollWidth / 2;          // نسختان متتاليتان
    setDuration(Math.max(30, Math.round(w / 55)));
  }, [rows.length, mode]);

  /* ══ الضغط يوقف، والاستئناف تلقائيّ ══
     كان الإيقاف يدوم حتى تُغادر الصفحة وتعود (`visibilitychange`) — أي أن
     من ضغط الشريط ليقرأ خبراً وجده **واقفاً إلى الأبد**، وليس في الواجهة
     ما يقول كيف يُستأنف. والغرض من الإيقاف قراءةُ سطرٍ عابر، وهي ثوانٍ.
     فيُستأنف وحده بعد ستّ ثوانٍ، وكلُّ ضغطةٍ جديدة تُجدّد المهلة. */
  const pausedRef = useRef(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pauseTrack = () => {
    const el = trackRef.current;
    if (!el) return;
    el.style.animationPlayState = "paused";
    pausedRef.current = true;
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => {
      if (trackRef.current) trackRef.current.style.animationPlayState = "";
      pausedRef.current = false;
    }, 6000);
  };
  useEffect(() => () => { if (resumeTimer.current) clearTimeout(resumeTimer.current); }, []);
  useEffect(() => {
    const resume = () => {
      if (!pausedRef.current || document.visibilityState !== "visible") return;
      if (trackRef.current) trackRef.current.style.animationPlayState = "";
      pausedRef.current = false;
    };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    return () => {
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
    };
  }, []);

  if (!isOwner) return null;

  const num = (v: any, d = 2) =>
    v == null ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  /* ══ صفرٌ لا مرجع له ليس تعادلاً ══
     يعيد الخادم `prev_close: null` متى غاب الإغلاق السابق عن المزوّد،
     ويبقى `change_pct` صفراً للتوافق الحسابيّ. وصفرٌ كهذا **ليس تعادلاً**
     بل جهلاً بالتغيّر — فلو عُرض تعادلاً لظهر المؤشّر محايداً في يومٍ
     تحرّك فيه، وهو ما لا يُغتفر في شريطٍ يُقرأ بنظرة.
     فيُقرأ غياباً: شرطةٌ وحبرٌ محايد، لا رقمٌ يوهم. */
  const noRef = !!tasi && tasi.prev_close == null;
  const tasiC = noRef ? null : tasi?.change_pct;
  const tasiDir = tasiC == null ? "fl" : tasiC > 0 ? "up" : tasiC < 0 ? "dn" : "fl";
  /* التعادل: الرقم والنسبة بحبر التطبيق الأساسيّ (أسود على الورق، أبيض
     على الداكن)، والسهمُ وحده أصفر. (بأمر المالك)
     وهو الصواب دلالةً أيضاً: اللون في هذا التطبيق يقول **اتجاهاً**، ولا
     اتجاه في التعادل. فيحمل السهمُ إشارةَ الحالة، ويبقى الرقم رقماً. */
  const tone = (v: any) =>
    v == null ? "var(--ink-muted)" : v > 0 ? "var(--pos-ink)" : v < 0 ? "var(--neg-ink)" : "var(--ink)";

  /* ══ حبرُ تاسي: ثلاثةُ ألوانٍ صريحةٍ ثابتة ══
     ثابتةٌ بمعنيين، وكلاهما مقصود:
      • **ثابتةٌ بين المظهرين**: اللسان سطحٌ بنفسجيّ لا يتبدّل بتبدّل
        المظهر، فلا معنى لحبرٍ يتبدّل فوق أرضيةٍ لا تتبدّل. ورموز الورق
        كانت تفعل ذلك فيسقط الرقم في المظهر الفاتح (قِيس ١٫٤٤:١).
      • **ثابتةٌ في المعنى**: أحمرُ هبوطٍ، أخضرُ صعودٍ، أبيضُ تعادل — لا
        كهرمانَ ولا رماديّ. التعادل حالةٌ محايدة، والأبيض حيادُ اللسان.
     ولا تُشتقّ من رموز الورق لأن أرضيتها ليست ورقاً. */
  const tabInk = (v: any) =>
    v == null || v === 0 ? "#ffffff" : v > 0 ? "#22c55e" : "#ff5252";

  const PHASES: Record<string, string> = {
    open: "السوق مفتوح", pre: "قبل الافتتاح",
    preclose: "قبل الإغلاق", closed: "السوق مغلق",
  };
  const stateText = PHASES[phase] || "السوق مغلق";
  const tasiText = `${num(tasi?.price, 2)}${
    tasiC == null ? " — لم يصل إغلاقُ الأمس، فلا تغيّرَ يُقاس"
                  : ` (${tasiC > 0 ? "+" : ""}${num(tasiC)}%)`}`;

  const pass = (k: string) =>
    rows.map((r: any, i: number) => {
      if (r.kind === "news") {
        return (
          <a className="mk-item mk-news" key={`${k}-n-${i}`} href={r.url || undefined}
             target="_blank" rel="noopener noreferrer">
            <span className="mk-news-dot" aria-hidden="true" />
            {r.source && <span className="mk-src">{r.source}</span>}
            <span className="mk-head">{r.headline}</span>
          </a>
        );
      }
      const c = Number(r.change_pct);
      const dir = c > 0 ? "up" : c < 0 ? "dn" : "fl";
      return (
        <span className="mk-item" key={`${k}-${r.symbol}-${i}`}>
          {/* السهم انتقل من صدر العنصر إلى **بين السعر ونسبته** (بأمر
              المالك): موضعه هناك يفصل الكمّية عن تغيّرها، وكان في الصدر
              يصف العنصر كلَّه فيُقرأ وسماً للشركة لا للحركة. */}
          <span className="mk-name">{r.name || r.symbol}</span>
          {r.price != null && (
            <span className="mk-price" dir="ltr" style={{ color: tone(c) }}>{num(r.price)}</span>
          )}
          <TrendArrow dir={dir as any} size={10}
            color={dir === "fl" ? "var(--flat-arrow)" : tone(c)} />
          <span className="mk-pct" dir="ltr" style={{ color: tone(c) }}>
            {c > 0 ? "+" : ""}{num(c)}%
          </span>
        </span>
      );
    });

  return (
    <div className="mk-ticker">
      {/* لسانٌ واحد بطولٍ ثابت — يتبدّل ما بداخله لا هو.
          في وضع السوق: حالةُ السوق · رقم تاسي · سهمٌ · نسبته.
          وفي وضع الأخبار: أيقونةٌ وكلمة «الأخبار».
          والطول مثبَّت في الرموز (١٦٨px) كي لا يقفز الشريط عند كل ضغطة. */}
      <button className="mk-tab" onClick={swap} type="button"
        /* التلميحة تبدأ بحالة السوق لا بكلمة «تاسي»: الرقم ظاهرٌ في اللسان
           أصلاً، فتكرارُ اسمه لا يضيف شيئاً — بينما «مفتوح» أو «مغلق» هي
           المعلومة التي لا يقولها الرقم، وعليها يتوقّف معناه. */
        title={mode === "market"
          ? `${stateText} · ${tasiText} — اضغط لعرض الأخبار`
          : "الأخبار — اضغط لعرض حركة السوق"}
        aria-label={mode === "market"
          ? `${stateText}. مؤشّر تاسي ${tasiText}. اضغط لعرض الأخبار`
          : "الأخبار. اضغط لعرض حركة السوق"}>
        <span className="mk-tab-slot">
          {mode === "news" ? (
            <>
              <Radio size={13} aria-hidden="true" />
              <span style={{ fontSize: 12, fontWeight: 700 }}>الأخبار</span>
            </>
          ) : (
            <>
              {/* حالة السوق: نبضةٌ حيّة أثناء الجلسة. وبعد الإغلاق دائرةٌ
                  بداخلها شرطة — رمزُ «موقوف» المتعارَف، يُقرأ بلا كلمة
                  ولا يُخلط بنقطةٍ ساكنة قد تبدو عطباً في الرسم. */}
              {/* ══ رمزُ الطور: مستقلٌّ بألوانه ══
                  ألوانه ليست من رموز الربح والخسارة ولا من حبر الشريط —
                  هو يصف **زمن الجلسة** لا اتجاه السعر، فخلطُه بلغة الأخضر
                  والأحمر يجعل «مفتوح» تُقرأ «صاعد». ولكلّ طورٍ شكلٌ يخصّه
                  أيضاً، فيُقرأ بلا لونٍ أصلاً:
                    مغلق        دائرةٌ فيها شرطة   أبيض
                    مفتوح       دائرةٌ ممتلئة      أخضر (تنبض)
                    قبل الافتتاح دائرةٌ ممتلئة     برتقاليّ صريح
                    قبل الإغلاق  هلالٌ سميك        أزرق صريح            */}
              {/* ══ أيقونة البثّ في الأطوار الحيّة · والإغلاق كما كان ══
                  (بأمر المالك)
                  الإغلاق يبقى على شكله الأصليّ: دائرةٌ بداخلها شرطة — رمزُ
                  «موقوف» المتعارَف، يُقرأ بلا لونٍ ولا كلمة. ولا معنى
                  لأيقونة بثٍّ حيث لا بثّ.
                  والألوان هي درجاتُ اللسان التي أقرّها المالك سابقاً بعد
                  عرضٍ على تدرّجه نفسه — لا درجاتٌ جديدة.
                  أمّا العتمة التي رآها فليست في الدرجة بل في **الشكل**:
                  الأيقونة مرسومةٌ بخطٍّ مفتوح لا بمساحةٍ ممتلئة كالنقطة
                  السابقة، والخطُّ الرفيع على أرضيةٍ نيليّة يُقرأ باهتاً وإن
                  كانت درجته هي هي. فغُلّظ الخطّ (‏2.6) وكُبّرت الأيقونة
                  درجة — تُعالَج العتمة من سببها لا برفع الإضاءة. */}
              {/* ══ شكلٌ لكلّ طور ══ (بأمر المالك)
                  قبل الافتتاح: نقطةٌ برتقالية تومض. مفتوح: مركزٌ ثابتٌ
                  وموجاتٌ تتدرّج. قبل الإغلاق: هلالٌ أزرق — قوسٌ ناقص
                  والنقصانُ هو المعنى. مغلق: قرصٌ أحمر بشرطةٍ بيضاء في
                  أصغر مقاسٍ يبقى مقروءاً. فاللونُ يؤكّد الطور ولا ينفرد
                  بحمله. */}
              {/* شعارُ تداول مكانَ رمز الطور (بأمر المالك). والطورُ باقٍ في
                  تلميحة اللسان ونصّه المسموع — لم تضِع المعلومة، تغيّر
                  حاملُها. */}
              {/* ══ الرفعُ بمقدارٍ مقيس ══ (بأمر المالك · D197)
                  طُلب أن يحاذي الرقمُ **منتصفَ الكلمتين** لا منتصفَ صندوق
                  الشعار — والفرقُ حقيقيّ: الرمزُ يعلو الكلمتين فيجرّ مركزَ
                  الصندوق إلى أعلى. قِيس في المتصفّح: أسفلُ «تداول» 18.04
                  وأعلى «Tadawul» 17.21 ⇐ منتصفُهما 17.63، وحبرُ الرقم 16.
                  فرُفع الشعارُ بالفرق (1.6px) لا بتقديرٍ بالعين. */}
              <span style={{ display: "inline-flex", transform: "translateY(-1.6px)" }}>
                <TadawulLogo height={15} wordColor="#ffffff" title={stateText} />
              </span>
              {/* ══ الرقم قيمة، والسهم والنسبة دلالة ══ (بأمر المالك)
                  كان الثلاثة يتلوّنون معاً، فيصير رقم المؤشّر نفسه أحمر —
                  وهو ليس ربحاً ولا خسارة، بل مستوى السوق. الدلالة تخصّ
                  **التغيّر** لا القيمة: فالرقم أبيضُ دائماً، والسهم والنسبة
                  وحدهما يحملان الأخضر أو الأحمر. */}
              <span className={`mk-tasi ${tasiDir}`}>
                <span className="mk-tab-val" dir="ltr" style={{ color: "#ffffff" }}>{num(tasi?.price, 2)}</span>
                {/* السهم بين الرقم ونسبته — يفصل الكمّية عن تغيّرها. */}
                <TrendArrow dir={tasiDir as any} size={11}
                  color={tasiDir === "fl" ? "var(--flat-arrow)"
                       : tasiDir === "up" ? "#22c55e" : "#ff5252"} />
                <span className="mk-tab-pct" dir="ltr" style={{ color: tabInk(tasiC) }}>
                  {tasiC == null ? "—" : `${tasiC > 0 ? "+" : ""}${num(tasiC)}%`}
                </span>
              </span>
            </>
          )}
        </span>
      </button>

      <div className="mk-view">
        {rows.length ? (
          <div className="mk-track" ref={trackRef} style={{ animationDuration: `${duration}s` }}
            onClick={pauseTrack}>
            {pass("a")}
            {pass("b")}
          </div>
        ) : (
          <div className="mk-empty">لم تصل حركة السوق بعد — تُحدَّث مع فحص السوق</div>
        )}
      </div>
    </div>
  );
}
