import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, Shield, Sparkles, ShieldCheck } from "lucide-react";
import { marketApi } from "../../services/api";
import { lookupCompany } from "../../data/saudiCompanies";
import { isTasiOpen } from "../../utils/marketHours";
import FlashPrice from "../common/FlashPrice";
import CompanyLogo from "../common/CompanyLogo";
import KeyFigures from "../common/KeyFigures";
import { ShariaBadge } from "../common/UI";
import AnalysisPanel from "../analysis/AnalysisPanel";
import FinancialsTable from "../analysis/FinancialsTable";
import DividendProfile from "../analysis/DividendProfile";
import StockOpinion from "../analysis/StockOpinion";
import StockCalendar from "../analysis/StockCalendar";
import CompanyProfileCards from "../analysis/CompanyProfileCards";
import PriceChart from "../analysis/PriceChart";
import OwnershipBar from "../analysis/OwnershipBar";
import clsx from "clsx";

/**
 * عرض الشركة الموحّد — بطاقة واحدة تخدم كل التطبيق (السوق · الحوكمة · رأي
 * الذكاء · المراقبة · بحث المحفظة) بلغةٍ تصميمية واحدة، فلا يختلف شكل الشركة
 * من قسمٍ لآخر. (صفحة الحيازات في «المحفظة» تحتفظ بتخطيطها الخاص.)
 *
 * قواعد التخطيط المعتمدة:
 *  • «إلغاء» زرٌّ بلا إطار في أقصى الزاوية العليا المقابلة للاسم — لا يزاحم
 *    الهوية ولا يأخذ صفّاً لنفسه.
 *  • صفّ الهوية الثاني: الرمز · القطاع · درجة الجودة المالية — نصٌّ متجاور بلا
 *    خلفيات ولا أُطر ولا كبسولات. الشارات المتراكمة تُشتّت، والنصّ النظيف
 *    يُقرأ أسرع.
 *  • نسبة التغيّر: سهم + رقم، بلا كبسولة دائرية حوله.
 *  • التبويبات: صفٌّ واحدٌ بلا إطار، فاصلُه خطٌّ سفليٌّ واحد والنشِطُ يُعلَّم
 *    بخطٍّ تحته — النمطُ نفسُه في صفحة الشركة، فلا يختلف شكلُ التبويب
 *    باختلاف الشاشة التي فُتح منها السهم.
 */

const govScoreColor = (g: any) => {
  if (!g?.evaluable || g?.score == null) return "var(--ink-muted)";
  const v = Number(g.score);
  return v >= 70 ? "var(--pos-ink)" : v >= 50 ? "var(--warn-ink)" : "var(--neg-ink)";
};

const fmt = (n: number, d = 2) => (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const compact = (n: number) => {
  if (n == null) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليار";
  if (a >= 1e6) return (n / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليون";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
};

const SECTOR_AR: Record<string, string> = {
  "Energy": "الطاقة", "Basic Materials": "المواد الأساسية", "Materials": "المواد الأساسية",
  "Industrials": "الصناعات", "Consumer Cyclical": "السلع الكمالية", "Consumer Defensive": "السلع الأساسية",
  "Financial Services": "الخدمات المالية", "Financials": "الخدمات المالية", "Healthcare": "الرعاية الصحية",
  "Technology": "التقنية", "Communication Services": "الاتصالات", "Utilities": "المرافق العامة", "Real Estate": "العقارات",
};
export function sectorAr(symbol: string, sector?: string | null) {
  const local = lookupCompany(symbol)?.sector;
  if (local) return local;
  if (!sector) return null;
  return SECTOR_AR[sector] || sector;
}

function DayRangeRow({ low, high }: { low: number; high: number }) {
  const open = isTasiOpen();
  return (
    <div className="flex items-center gap-2 flex-wrap text-[11px] text-[var(--ink-muted)]">
      {open ? (
        <span className="flex items-center gap-1 font-semibold text-[var(--pos-ink)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--pos-ink)] animate-pulse" /> مباشر
        </span>
      ) : <span className="font-semibold">السوق مغلق</span>}
      <span>نطاق اليوم:</span>
      <span className="tabular-nums" dir="ltr">{fmt(low)} — {fmt(high)}</span>
    </div>
  );
}

/* ══ التبويبات: النمطُ نفسُه في كلّ مكانٍ يُعرض فيه سهم ══
   كانت هذه الورقةُ عمودين مؤطَّرين وصفحةُ الشركة صفّاً واحداً بلا إطار،
   والمكوّنان يعرضان الشيءَ نفسَه — فيرى المالكُ شكلين لشاشةٍ واحدة.
   فوُحّدا على نمط `CompanyPage`: صفٌّ واحدٌ بفاصلٍ سفليٍّ واحد، واسمٌ
   قصيرٌ للجوّال وكاملٌ لما اتّسع — بلا تمريرٍ أفقيّ ولا التفافِ سطر. */
const TABS = [
  { id: "overview", label: "نظرة عامة", short: "نظرة" },
  { id: "analysis", label: "تقييم الأداء", short: "الأداء" },
  { id: "financials", label: "القوائم المالية", short: "القوائم" },
  { id: "dividends", label: "التوزيعات", short: "التوزيعات" },
  { id: "calendar", label: "المفكرة", short: "المفكرة" },
  { id: "opinion", label: "رأي الذكاء", short: "الذكاء", color: true },
] as const;

export default function StockView({ symbol, onClose }: { symbol: string; onClose?: () => void }) {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");

  const { data, isLoading } = useQuery({
    queryKey: ["analysis", symbol],
    queryFn: () => marketApi.company(symbol).then(r => r.data.data),
    enabled: !!symbol,
    retry: 0,
  });


  const gov = data?.governance;
  const sector = sectorAr(symbol, data?.sector);
  const up = (data?.change_pct ?? 0) >= 0;

  return (
    <div className="space-y-4">
      {/* ── الهوية ── */}
      <div className="relative">
        <div className="flex items-center gap-3">
          <CompanyLogo symbol={symbol} size={40} logoUrl={data?.logo_url} />
          <div className="min-w-0">
            {/* ══ الإلغاءُ بجانب الاسم لا في زاوية البطاقة ══ (بأمر المالك)
                كان في أقصى الطرف، فمن أراد إلغاءَ بحثه قطع الشاشةَ بعينه
                ويده. والفعلُ يخصّ هذه الشركةَ فمحلُّه عندها. */}
            <div className="flex items-center gap-2 min-w-0">
              <ShariaBadge status={data?.sharia_status} size={15} />
              <h2 className="text-lg font-bold text-[var(--ink)] truncate">{lookupCompany(symbol)?.name_ar || data?.name || symbol}</h2>
              {onClose && (
                <button onClick={onClose} title="إلغاء" aria-label="إلغاء"
                  className="stock-close shrink-0 p-1 rounded-lg">
                  <X size={15} />
                </button>
              )}
            </div>
            {/* صفٌّ واحد نظيف: الرمز · القطاع · الحوكمة — بلا خلفيات ولا أُطر. */}
            <div className="flex items-center gap-x-3 gap-y-1 mt-1 flex-wrap text-xs text-[var(--ink-muted)]">
              <span className="tabular-nums font-semibold text-[var(--ink-muted)]" dir="ltr">{symbol}</span>
              {sector && <span>{sector}</span>}
              {gov && (
                <span className="flex items-center gap-1" title={gov.narrative || "درجة الجودة المالية"}>
                  <ShieldCheck size={13} style={{ color: govScoreColor(gov) }} className="shrink-0" />
                  {gov.evaluable && gov.score != null ? (
                    <span className="font-bold tabular-nums" style={{ color: govScoreColor(gov) }}>
                      {Math.round(gov.score)}
                    </span>
                  ) : (
                    <span className="font-semibold text-[var(--ink-muted)]">بيانات غير كافية</span>
                  )}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── التبويبات: صفٌّ واحدٌ بلا إطار — نمطُ صفحة الشركة نفسُه ── */}
      <div className="flex items-stretch gap-0.5 sm:gap-1 border-b border-[var(--hairline)]"
           role="tablist" aria-label="أقسام الورقة">
        {TABS.map(tb => {
          const on = tab === tb.id;
          const isAi = Boolean((tb as any).color);
          return (
            <button key={tb.id} onClick={() => setTab(tb.id)}
              role="tab" aria-selected={on}
              className={clsx(
                "flex-1 min-w-0 flex items-center justify-center gap-1",
                "px-0.5 sm:px-2 py-2 text-[10.5px] sm:text-xs font-bold",
                "border-b-2 -mb-px transition-colors whitespace-nowrap",
                on ? "border-[var(--brand)]" : "border-transparent",
                on ? (isAi ? "" : "text-[var(--brand-ink)]")
                   : "text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              {isAi && <Sparkles size={11} className={on ? "ai-star" : ""} />}
              <span className={clsx("truncate", isAi && on && "ai-opinion-text")}>
                <span className="sm:hidden">{tb.short}</span>
                <span className="hidden sm:inline">{tb.label}</span>
              </span>
            </button>
          );
        })}
      </div>

      {tab === "overview" && (
        isLoading ? <div className="h-40 skeleton" /> : (!data || data.unavailable_reason) ? (
          /* السببُ يُقال ولا يُنسب إلى الورقة: «لا توجد بيانات لهذا الرمز»
             تدفع المالك إلى حذف ورقةٍ سليمة، وحصّةُ المصدر إن نفدت فذاك
             حدُّ أداتنا لا نقصٌ في السهم. */
          <div className="py-10 text-center text-[var(--ink-muted)] text-sm px-6">
            {data?.unavailable_reason || "لم تصلنا بياناتُ هذا الرمز من مصدرنا الآن."}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="space-y-3 min-w-0">
              {data.price != null && (
                <div className="flex items-baseline gap-3">
                  <FlashPrice value={data.price} className="text-2xl font-bold text-[var(--ink)] tabular-nums">{fmt(data.price)} ﷼</FlashPrice>
                  {data.change_pct != null && (
                    /* سهم + رقم، بلا كبسولة — الاتجاه يُقرأ من الشكل واللون معاً. */
                    <span className={"text-sm font-bold tabular-nums " + (up ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>
                      <span className="chg-arrow">{up ? "▲" : "▼"}</span> {(up ? "+" : "") + data.change_pct.toFixed(2)}%
                    </span>
                  )}
                </div>
              )}
              {data.day_low != null && data.day_high != null && data.day_high > data.day_low && (
                <DayRangeRow low={data.day_low} high={data.day_high} />
              )}
              {/* ══ سطران لا سطر: قيمةٌ عادلة ومتوسطُ سعر ══ (بأمر المالك)
                  كان سطرٌ واحد اسمه «السعر العادل» ورقمُه متوسطٌ متحرّك،
                  فيخالف صفحة الذكاء التي تعرض إجماع أهداف المحللين تحت
                  الاسم نفسه. الآن القيمة العادلة من المصدر الموحَّد،
                  والمتوسط المتحرّك يظهر باسمه — رقمان مختلفان لأنهما
                  مفهومان مختلفان، وكلٌّ يقول ما هو. */}
              {/* ══ رقمان يظهران هنا كما يظهران في تقييم الأداء ══
                  (بأمر المالك: «هل أصبح الجميع متطابقين؟»)
                  كانت صفحةُ الشركة عند البحث تعرض القيمة العادلة وحدها،
                  وتسمّيها **«إجماع المحللين»** — وقد أُخرج المحللون من
                  حساب القيمة (‏D047)، فالاسمُ يصف مصدراً لم يعد قائماً.
                  ودرجةُ الحوكمة كانت غائبةً عن هذه الشاشة رغم أنها في
                  الاستجابة نفسها. فصار الرقمان هنا بالاسمين نفسيهما
                  وبالمصدر نفسه — لا رقمَ في شاشةٍ وغيابٌ في أخرى. */}
              {/* ══ الدرجةُ والقرارُ لا يُكرَّران في «نظرة عامة» ══
                  (بأمر المالك) — موضعُهما تبويبُ «تقييم الأداء» والنجمة،
                  وهما هناك بالمجلس الذي يفسّرهما. وتكرارُهما هنا مجرَّدين
                  من مجلسهما يزاحم صفَّ السعر ولا يضيف قراراً. */}
              {data.fair_value != null && (
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className="text-[var(--ink-muted)]">هدف المحللين</span>
                  <span className={"font-bold tabular-nums " + ((data.fair_value_upside_pct ?? 0) > 0 ? "text-[var(--pos-ink)]" : (data.fair_value_upside_pct ?? 0) < 0 ? "text-[var(--neg-ink)]" : "text-[var(--ink-muted)]")}>
                    {fmt(data.fair_value)} ﷼{data.fair_value_upside_pct != null && ` (${data.fair_value_upside_pct > 0 ? "+" : ""}${data.fair_value_upside_pct}%)`}
                  </span>
                </div>
              )}
              {/* متوسط السعر المتحرّك أُسقط من هنا بأمر المالك: لا يعنيه،
                  ووجودُه بجانب القيمة العادلة يُغري بالخلط بينهما. وهو
                  باقٍ في «التحليل الفني» حيث يخصّ. */}
            </div>
            {/* الشبكةُ مكوّنٌ مشتركٌ مع صفحة الشركة في الحيازات — تصميمٌ
                واحدٌ لا نسختان (بأمر المالك). */}
            <KeyFigures fundamentals={data?.fundamentals} />
            <PriceChart symbol={symbol} />
            <OwnershipBar symbol={symbol} />
            {/* ══ بطاقةُ التوافق الشرعيّ حُذفت ══ (بأمر المالك)
                الهلالُ في ترويسة الصفحة يقول الحكمَ بلونه وتلميحه، فبطاقةٌ
                كاملةٌ تحته تكرارٌ لِما قيل. وموضعُ التفصيل صفحةُ الشركة في
                الحيازات — هناك تحت الهيكلة مكاناً ثابتاً. */}
            <CompanyProfileCards symbol={symbol} />
          </div>
        )
      )}

      {tab === "analysis" && <AnalysisPanel symbol={symbol} name={data?.name} />}
      {tab === "financials" && <FinancialsTable symbol={symbol} />}
      {tab === "dividends" && <DividendProfile symbol={symbol} />}
      {tab === "calendar" && <StockCalendar symbol={symbol} name={data?.name} />}
      {tab === "opinion" && (
        <div className="card">
          <StockOpinion symbol={symbol} name={data?.name} />
        </div>
      )}
    </div>
  );
}
