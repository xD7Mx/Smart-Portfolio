import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, X, Share2, ExternalLink, Loader2 } from "lucide-react";
import CompanyLogo from "../common/CompanyLogo";
import { lookupCompany } from "../../data/saudiCompanies";
import { marketApi } from "../../services/api";
import { ShareButton, ArgaamButton } from "../common/ShareOpen";

/**
 * اللغة التصميمية الموحدة للمفكرة — every corporate-action announcement is
 * rendered the same way everywhere (market calendar, portfolio calendar):
 * the company's real logo + a typed action pill (توزيع/أحقية/منحة/...) +
 * name/symbol/date, grouped by week ("الترتيب الأسبوعي"). The مفكرة is
 * strictly corporate actions — never general news (kept isolated upstream
 * by the calendar keyword governance).
 */

/* ══ وسمُ نوع الحدث: أرضيةٌ صلبة وحبرٌ أسود ══ (بأمر المالك)
   كانت الوسوم مفرَّغة (أرضيةٌ شفّافة وحبرٌ ملوّن) — تُقرأ نصّاً ملوّناً لا
   وسماً، وتذوب في صفٍّ مزدحم. والوسم الآن **رقعةٌ مستطيلة بلونٍ واحد
   صلب** وحبرٌ أسود دائماً في المظهرين.

   ولماذا الحبر أسودُ ثابتٌ لا يتبع المظهر: الرقعة لونُها لا يتبدّل، فحبرٌ
   يتبدّل فوقها يسقط في أحد المظهرين حتماً. والأسود على هذه الدرجات
   الفاتحة يعطي ٩:١ فما فوق — قِيست كلُّها.

   والألوان دلالية لا زخرفية: أصفرُ للإعلان العامّ، أخضرُ للتوزيع،
   سماويّ للجمعية، بنفسجيّ للمنحة، كهرمانيّ للنتائج، ورديّ للاندماج. */
/* لكل نوعٍ حبرُه — لا حشوَ ولا إطار (بأمر المالك: «خليها مثل الوسوم
   اللي في التبويبات الأخرى»). و«موعد الأحقية» نوعٌ قائمٌ بذاته لا
   مرادفٌ للتوزيع: الأحقيةُ تاريخُ **الاستحقاق** — من ملك السهم قبله
   استحقّ — والصرفُ تاريخُ وصول النقد. وهما قراران مختلفان تماماً،
   وكان الوسمان يقولان «توزيع أرباح» معاً فيتساويان في المسح البصريّ
   ولا يُفرَّق بينهما إلا بقراءة السطر الصغير تحتهما. */
const TYPE_META: Record<string, { label: string; bg: string; fg: string }> = {
  DIVIDEND:     { label: "صرف أرباح",        bg: "var(--tag-dividend)", fg: "var(--tag-ink)" },
  ELIGIBILITY:  { label: "موعد أحقية",       bg: "var(--tag-eligibility)", fg: "var(--tag-ink)" },
  RIGHTS_ISSUE: { label: "حقوق أولوية",      bg: "var(--tag-rights)", fg: "var(--tag-ink)" },
  BONUS:        { label: "أسهم منحة",        bg: "var(--tag-bonus)", fg: "var(--tag-ink)" },
  SPLIT:        { label: "تجزئة",            bg: "var(--tag-split)", fg: "var(--tag-ink)" },
  RESULTS:      { label: "نتائج مالية",      bg: "var(--tag-results)", fg: "var(--tag-ink)" },
  MERGER:       { label: "اندماج واستحواذ",  bg: "var(--tag-merger)", fg: "var(--tag-ink)" },
  ACQUISITION:  { label: "اندماج واستحواذ",  bg: "var(--tag-merger)", fg: "var(--tag-ink)" },
  AGM:          { label: "جمعية عمومية",     bg: "var(--tag-agm)", fg: "var(--tag-ink)" },
  OTHER:        { label: "إعلان",            bg: "var(--tag-news)", fg: "var(--tag-ink)" },
};
// Arabic kind labels used by per-company calendars ({kind: "توزيع" | "أحقية"...})
const KIND_TO_TYPE: Record<string, string> = {
  "توزيع": "DIVIDEND", "صرف أرباح": "DIVIDEND",
  "أحقية": "ELIGIBILITY", "احقية": "ELIGIBILITY", "موعد أحقية": "ELIGIBILITY", "منحة": "BONUS", "تجزئة": "SPLIT",
  "زيادة رأس المال": "RIGHTS_ISSUE", "حقوق أولوية": "RIGHTS_ISSUE",
  "نتائج": "RESULTS", "جمعية": "AGM", "الجمعية العامة": "AGM",
  "اندماج": "MERGER", "استحواذ": "ACQUISITION", "معلومة": "OTHER",
};

/* ══ الوسم يُحلّ بالمرور على كل المرشّحين ══
   كان: `e.type || e.event_type || KIND_TO_TYPE[e.kind] || "OTHER"` — وهي
   سلسلةٌ تتوقّف عند **أوّل قيمةٍ موجودة** لا أوّل قيمةٍ مفهومة. ومفكرةُ
   الشركة تُرسل `type` بالعربية (‏«توزيع» · «أحقية» · «جمعية») لأن
   `get_events` يكتب `"type": it.get("kind")`. فيُلتقط العربيُّ أوّلاً،
   ويُبحث عنه في جدولٍ مفاتيحُه إنجليزية، فلا يوجد — فتسقط **كلُّ** صفوف
   مفكرة الشركة إلى OTHER = «إعلان». وهكذا ظهر «موعد أحقية» إعلاناً.
   والعلّة أن الشرط خلط «موجود» بـ«صالح». فصار المرور على المرشّحين
   واحداً واحداً، وكلُّ مرشّحٍ يُجرَّب في الجدولين: المغلق أوّلاً ثم
   جدول الألفاظ العربية. */
function typeMeta(e: any) {
  for (const raw of [e.type, e.event_type, e.kind]) {
    if (!raw || typeof raw !== "string") continue;
    const direct = TYPE_META[raw.toUpperCase()];
    if (direct) return direct;
    const mapped = TYPE_META[KIND_TO_TYPE[raw.trim()]];
    if (mapped) return mapped;
  }
  return TYPE_META.OTHER;
}

const DAY = 24 * 3600 * 1000;
function weekStart(d: Date): number {
  // Saudi business week starts Sunday.
  const x = new Date(d); x.setHours(0, 0, 0, 0);
  return x.getTime() - x.getDay() * DAY;
}

/** Natural, professional time buckets — اليوم / هذا الأسبوع / الأسبوع القادم /
 * هذا الشهر / الشهر القادم / لاحقاً, then أمس / الأسبوع الماضي / الشهر الماضي /
 * سابقاً for history — the familiar ordering readers know from mainstream
 * finance apps. Lower rank renders first. */
function bucketOf(dateMs: number, now: Date): { rank: number; label: string } {
  const today = new Date(now); today.setHours(0, 0, 0, 0);
  const t0 = today.getTime();
  const thisWeek = weekStart(now);
  const nextWeek = thisWeek + 7 * DAY;
  const weekAfter = thisWeek + 14 * DAY;
  const lastWeek = thisWeek - 7 * DAY;
  const m = now.getMonth(), y = now.getFullYear();
  const monthStart = new Date(y, m, 1).getTime();
  const nextMonthStart = new Date(y, m + 1, 1).getTime();
  const monthAfterStart = new Date(y, m + 2, 1).getTime();
  const lastMonthStart = new Date(y, m - 1, 1).getTime();

  if (dateMs >= t0 && dateMs < t0 + DAY) return { rank: 0, label: "اليوم" };
  if (dateMs >= t0 + DAY && dateMs < t0 + 2 * DAY) return { rank: 1, label: "غداً" };
  if (dateMs >= thisWeek && dateMs < nextWeek && dateMs >= t0) return { rank: 2, label: "هذا الأسبوع" };
  if (dateMs >= nextWeek && dateMs < weekAfter) return { rank: 3, label: "الأسبوع القادم" };
  if (dateMs >= weekAfter && dateMs < nextMonthStart) return { rank: 4, label: "هذا الشهر" };
  if (dateMs >= nextMonthStart && dateMs < monthAfterStart) return { rank: 5, label: "الشهر القادم" };
  if (dateMs >= monthAfterStart) return { rank: 6, label: "لاحقاً" };
  // ── past ──
  if (dateMs >= t0 - DAY && dateMs < t0) return { rank: 7, label: "أمس" };
  if (dateMs >= thisWeek && dateMs < t0) return { rank: 8, label: "هذا الأسبوع — سابقاً" };
  if (dateMs >= lastWeek && dateMs < thisWeek) return { rank: 9, label: "الأسبوع الماضي" };
  if (dateMs >= monthStart && dateMs < thisWeek) return { rank: 10, label: "هذا الشهر — سابقاً" };
  if (dateMs >= lastMonthStart && dateMs < monthStart) return { rank: 11, label: "الشهر الماضي" };
  return { rank: 12, label: "سابقاً" };
}

const fmtDate = (d: string) =>
  d ? new Date(d).toLocaleDateString("ar-SA-u-ca-gregory-nu-latn", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";

/**
 * نافذة تفاصيل الإعلان — نفس سلوك الأخبار: الضغط يفتح نافذة داخل التطبيق
 * لا انتقالاً مباشراً لموقع خارجي. والخروج للمصدر يبقى خياراً صريحاً، ولا
 * يظهر زرّه إلا بعد التحقّق من أن الرابط يفتح فعلاً (نفس حوكمة الأخبار:
 * لا نعرض زراً يقود لصفحة خطأ).
 */
function EventDetailModal({ e, onClose }: { e: any; onClose: () => void }) {
  const meta = typeMeta(e);
  const name = lookupCompany(e.symbol)?.name_ar || e.company_name || e.name;
  const title = e.title || e.headline || meta.label;
  const [link, setLink] = useState<{ state: "checking" | "ok" | "bad"; url?: string }>(
    e.url ? { state: "checking" } : { state: "bad" }
  );
  React.useEffect(() => {
    if (!e.url) return;
    let alive = true;
    marketApi.resolveNewsUrl(e.url)
      .then(r => { const u = r.data?.data?.url; if (alive) setLink(u ? { state: "ok", url: u } : { state: "bad" }); })
      .catch(() => { if (alive) setLink({ state: "bad" }); });
    return () => { alive = false; };
  }, [e.url]);

  /* نصّ الإعلان الكامل — يُجلب عند الفتح فقط. ثلاث حالاتٍ صريحة لا رابعة:
     يُجلب · وصل · تعذّر. ولا حالةَ صامتة تترك المالك ينتظر مربّعاً فارغاً. */
  const [detail, setDetail] = useState<{ s: "off" | "load" | "ok" | "bad"; t?: string }>(
    e.detail_id ? { s: "load" } : { s: "off" }
  );
  React.useEffect(() => {
    if (!e.detail_id) return;
    let alive = true;
    marketApi.eventDetail(String(e.detail_id))
      .then(r => { const t = r.data?.data?.text; if (alive) setDetail(t ? { s: "ok", t } : { s: "bad" }); })
      .catch(() => { if (alive) setDetail({ s: "bad" }); });
    return () => { alive = false; };
  }, [e.detail_id]);

  const share = async () => {
    const url = link.url || e.url || window.location.href;
    const data = { title, text: title, url };
    if ((navigator as any).share) {
      try { await (navigator as any).share(data); } catch { /* أُلغيت */ }
    } else {
      try { await navigator.clipboard.writeText(url); } catch { /* لا شيء */ }
    }
  };

  return (
    <div className="modal-overlay" onClick={ev => { if (ev.target === ev.currentTarget) onClose(); }}>
      <div className="modal-box fade-in" style={{ maxWidth: 480 }}>
        <div className="flex items-center justify-between mb-4">
          {e.symbol ? <CompanyLogo symbol={e.symbol} size={40} /> : <CalendarDays size={26} className="text-[var(--brand-ink)]" />}
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>
        <div className="flex items-center gap-2 flex-wrap mb-2.5">
          {name && <span className="tag-b" style={{ fontSize: 10 }}>{name}{e.symbol ? ` (${e.symbol})` : ""}</span>}
          <span className="ev-tag ms-auto" style={{ background: meta.bg, color: meta.fg }}>{meta.label}</span>
        </div>
        <h2 className="text-lg font-bold text-[var(--ink)] leading-snug mb-2">{title}</h2>
        <p className="text-xs text-[var(--ink-muted)] flex items-center gap-1.5 mb-4">
          <CalendarDays size={12} />
          {[fmtDate(e.date), e.source].filter(Boolean).join(" · ")}
        </p>
        {detail.s !== "off" && (
          <div className="mb-4 rounded-xl p-3" style={{ background: "var(--surface)" }}>
            {detail.s === "load" && (
              <span className="text-xs flex items-center gap-1.5" style={{ color: "var(--ink-muted)" }}>
                <Loader2 size={12} className="animate-spin" /> يُجلب نصّ الإعلان…
              </span>
            )}
            {detail.s === "ok" && (
              <p className="text-[12.5px] leading-relaxed whitespace-pre-line" style={{ color: "var(--ink)" }}>
                {detail.t}
              </p>
            )}
            {/* تعذّرٌ يُقال، لا يُخفى: بلا هذه الجملة يقرأ المالك الفراغ على
                أنه «لا تفاصيل لهذا الإعلان» — وهو غير صحيح. */}
            {detail.s === "bad" && (
              <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
                تعذّر جلب نصّ الإعلان — افتحه في أرقام.
              </span>
            )}
          </div>
        )}
        <div className="flex gap-2 flex-wrap">
          <ShareButton title={title} url={link.url || e.url} />
          {link.state === "checking" && (
            <span className="btn-ghost flex items-center gap-1.5 opacity-60"><Loader2 size={14} className="animate-spin" /> المصدر</span>
          )}
          {link.state === "ok" && (
            <a href={link.url} target="_blank" rel="noopener noreferrer" className="btn-ghost flex items-center gap-1.5">
              <ExternalLink size={14} /> المصدر
            </a>
          )}
          {/* «افتح في أرقام» بالرمز لا بالمعرّف المرفق: الإعلان قد يأتي من
              ياهو بلا معرّف أرقام، والشركة نفسها معروفة في الخريطة. فربطُ
              الزرّ بالرمز يجعله يظهر لكل شركةٍ في السوق لا للمنسوب وحده —
              وهو سبب غيابه عن المالك. */}
          <ArgaamButton symbol={e.symbol} />
        </div>
      </div>
    </div>
  );
}

function EventRow({ e, onOpen }: { e: any; onOpen: () => void }) {
  const meta = typeMeta(e);
  const name = lookupCompany(e.symbol)?.name_ar || e.company_name || e.name;
  return (
    <button onClick={onOpen} className="w-full text-start block active:scale-[.995] transition-transform">
      <div className="event-item flex items-center gap-3 p-2.5 rounded-xl transition-colors">
        {e.symbol ? <CompanyLogo symbol={e.symbol} size={32} /> : null}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            {/* الوسمُ بعد الرمز يساراً (بأمر المالك) — لا يزاحم الاسمَ والرمز. */}
            {name && <span className="text-[var(--ink)] text-[13px] font-semibold truncate">{name}</span>}
            {e.symbol && <span className="tag-b shrink-0" style={{ fontSize: 10 }}>{e.symbol}</span>}
            <span className="ev-tag shrink-0 ms-auto" style={{ background: meta.bg, color: meta.fg }}>{meta.label}</span>
          </div>
          <p className="text-[var(--ink-muted)] text-xs mt-1 leading-snug">{e.title || e.headline || meta.label}</p>
          <p className="text-[var(--ink-muted)] text-[11px] mt-0.5">{fmtDate(e.date)}</p>
        </div>
      </div>
    </button>
  );
}

/**
 * المفكرة والإفصاحات — قسمان في تبويبٍ واحد.
 *
 * خلطُهما كان يُنتج قائمةً لا يُقرأ منها شيء: «جمعية أرامكو يوم ٢١» موعدٌ
 * قادم تُخطِّط له، و«باعظيم وقّعت عقداً» خبرٌ وقع لا موعد. وحين يتجاوران
 * تحت ترويسة «اليوم» يظنّ المالك الثاني موعداً.
 *
 * فصارا مفصولين هنا بمُبدِّلٍ في رأس التبويب — لا بتبويبٍ ثانٍ في القائمة:
 * كلاهما «ما يخصّ شركاتي زمنياً»، وتفريقهما إلى وجهتين يزيد الطريق.
 * والفصل بالوسم `date_kind === "announced"` لا بالمصدر، فالمعيار **طبيعة
 * التاريخ** لا من جلبه.
 */
/* ══ لوحةُ توصيات المحللين ══
   الفراغ يبقى فراغاً: لا إجماعَ ياهو يُدسّ مكان توصيةِ بيتِ خبرةٍ سعوديّ،
   ولا سعرَ هدفٍ يُختلق. وغيابُ الهدف يُقال «—» ولا يُملأ بالسعر الحاليّ. */
/* أرضيةُ وسم التوصية — فاتحةٌ من عائلة وسوم الأحداث. كانت أحبارَ الحالة
   الداكنة أرضياتٍ (‏--pos-ink وأخواتها) فبدا التبويبُ معتماً ثقيلاً، وهي
   الشكوى الوحيدة التي رفعها المالك عن الوسوم. */
const VERDICT_TONE = (v: string) =>
  /شراء|زيادة|تفوق/.test(v) ? "var(--tag-buy)"
  : /بيع|تخفيض|أقل/.test(v) ? "var(--tag-sell)"
  : "var(--tag-hold)";

function RecsPanel({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-12 skeleton" />)}</div>;
  const rows: any[] = data?.rows || [];
  if (!rows.length) return (
    <div className="py-12 text-center text-[var(--ink-muted)] text-sm">
      لا توجد توصيات محللين متاحة من «أرقام» لهذه الشركة
    </div>
  );
  return (
    <div className="divide-y divide-[var(--hairline)]">
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2 py-2.5">
          <span className="ev-tag shrink-0"
            style={{ background: VERDICT_TONE(r.verdict), color: "var(--tag-ink)" }}>
            {r.verdict}
          </span>
          <span className="text-[var(--ink)] text-[12.5px] truncate flex-1 min-w-0">{r.house || "—"}</span>
          <span className="text-[var(--ink)] text-[12.5px] tabular-nums shrink-0" dir="ltr">
            {r.target != null ? r.target.toLocaleString("en-US", { minimumFractionDigits: 2 }) : "—"}
          </span>
          <span className="text-[var(--ink-muted)] text-[10.5px] tabular-nums shrink-0" dir="ltr">{r.date || "—"}</span>
        </div>
      ))}
    </div>
  );
}

export default function EventsList({ events, symbol }: { events: any[]; symbol?: string }) {
  const now = new Date();
  const [open, setOpen] = useState<any | null>(null);
  const [view, setView] = useState<"cal" | "disc" | "recs">("cal");

  /* ══ توصيات المحللين ══ (بأمر المالك)
     تبويبٌ ثالث في المُبدِّل نفسه، ومن «أرقام» كالمفكرة. ولا يُجلب إلا
     حين يُفتَح (`enabled`): من لا يفتحه لا يدفع ثمن نداءٍ لا يراه.
     ولا يظهر إلا حين يُعرف الرمز — في مفكرة السوق لا شركةَ بعينها. */
  const { data: recs, isLoading: recsLoading } = useQuery({
    queryKey: ["argaam-recs", symbol],
    queryFn: () => marketApi.recommendations(symbol!).then(r => r.data?.data),
    enabled: !!symbol && view === "recs",
    retry: 0,
  });

  const all = events || [];
  const discCount = all.filter((x: any) => x?.date_kind === "announced").length;
  const calCount = all.length - discCount;
  // لا يُعرض المُبدِّل إلا حين يوجد الجانبان: زرٌّ لقسمٍ فارغ يَعِد بما لا يجد.
  const split = discCount > 0 && calCount > 0;
  const shown = !split ? all
    : all.filter((x: any) => (view === "disc") === (x?.date_kind === "announced"));
  // Group into natural time buckets; upcoming buckets first (اليوم → لاحقاً),
  // then history (أمس → سابقاً). Inside a bucket: upcoming ascending,
  // past descending (most recent first).
  const groups = new Map<number, { label: string; items: any[] }>();
  const undated: any[] = [];
  for (const raw of shown) {
    /* إعلانٌ نعرف متى صدر لا متى يقع: تبويبه بتاريخ صدوره صحيح، لكن نصّه
       يجب أن يقوله — وإلا قرأه المالك تحت «اليوم» كأنه موعد اليوم. هنا
       مكانه لأن هذه القائمة هي العارض الوحيد لمفكرتَي الشركة والسوق معاً. */
    const e = raw?.date_kind === "announced" && !/^أُعلن/.test(raw?.title || "")
      ? { ...raw, title: "أُعلن: " + (raw.title || "") }
      : raw;
    if (!e?.date) { undated.push(e); continue; }
    const ms = new Date(e.date).getTime();
    if (isNaN(ms)) { undated.push(e); continue; }
    const b = bucketOf(ms, now);
    if (!groups.has(b.rank)) groups.set(b.rank, { label: b.label, items: [] });
    groups.get(b.rank)!.items.push(e);
  }
  const ordered = [...groups.keys()].sort((a, b) => a - b);

  /* المُبدِّل يظهر متى وُجد أكثر من جانبٍ واحد — وتبويب التوصيات جانبٌ
     قائم بذاته، فيُظهره وجودُ رمزِ شركةٍ حتى لو كانت المفكرة كلُّها من
     صنفٍ واحد. */
  const showSwitch = split || !!symbol;
  const switcher = showSwitch ? (
    /* الأسماء مجرّدة بلا أعداد بين قوسين (بأمر المالك): العدد يتغيّر مع كل
       تحديث فيقفز عرض الزرّ، والاسم وحده أرسم. */
    <div className="seg flex mb-3" role="tablist" aria-label="المفكرة والإفصاحات وتوصيات المحللين">
      <button role="tab" aria-selected={view === "cal"} className={"seg-btn" + (view === "cal" ? " on" : "")}
        onClick={() => setView("cal")}>المفكرة</button>
      <button role="tab" aria-selected={view === "disc"} className={"seg-btn" + (view === "disc" ? " on" : "")}
        onClick={() => setView("disc")}>الإفصاحات</button>
      {symbol && (
        <button role="tab" aria-selected={view === "recs"} className={"seg-btn" + (view === "recs" ? " on" : "")}
          onClick={() => setView("recs")}>توصيات المحللين</button>
      )}
    </div>
  ) : null;

  if (view === "recs") return <div>{switcher}<RecsPanel data={recs} loading={recsLoading} /></div>;

  if (!ordered.length && !undated.length) {
    return (
      <div>
        {switcher}
        <div className="py-16 text-center text-[var(--ink-muted)] text-sm">
          {view === "disc" ? "لا توجد إفصاحات حالياً" : "لا توجد إعلانات شركات حالياً"}
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {switcher}
      {ordered.map(rank => {
        const g = groups.get(rank)!;
        const past = rank >= 7;
        return (
          <div key={rank}>
            <p className="text-[11px] font-bold text-[var(--ink-muted)] mb-2 flex items-center gap-2">
              <span className={"w-1.5 h-1.5 rounded-full inline-block " + (past ? "bg-[var(--ink-muted)]" : "bg-[var(--brand)]")} />
              {g.label}
            </p>
            <div className="space-y-1.5">
              {g.items
                .sort((a, b) => {
                  const d = new Date(a.date).getTime() - new Date(b.date).getTime();
                  return past ? -d : d;
                })
                .map((e, i) => <EventRow key={e.id ?? `${rank}-${i}`} e={e} onOpen={() => setOpen(e)} />)}
            </div>
          </div>
        );
      })}
      {undated.length > 0 && (
        <div>
          <p className="text-[11px] font-bold text-[var(--ink-muted)] mb-2">بلا تاريخ محدد</p>
          <div className="space-y-1.5">{undated.map((e, i) => <EventRow key={`u-${i}`} e={e} onOpen={() => setOpen(e)} />)}</div>
        </div>
      )}
      {open && <EventDetailModal e={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
