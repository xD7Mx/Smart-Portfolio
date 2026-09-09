import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Newspaper, CalendarDays, Sparkles, Brain, Clock, ShieldCheck, X, Share2, ExternalLink, ArrowUp, ArrowDown, LayoutGrid, Star, Search, Plus, SlidersHorizontal, ArrowUpDown, ChevronDown } from "lucide-react";
import { marketApi } from "../services/api";
import { useT } from "../i18n";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import { searchCompanies, SECTORS } from "../data/saudiCompanies";
import StockSheet from "../components/market/StockSheet";
import InlineStockSearch from "../components/market/InlineStockSearch";
import CompanyLogo from "../components/common/CompanyLogo";
import { FairValueBar, SafetyBar, fairValueTier, safeColor } from "../components/common/ValueBars";
import SourceLogo, { hasSourceLogo } from "../components/common/SourceLogo";
import EventsList from "../components/market/EventsList";
import {
  IndexHistoryCard, SectorHeatmapCard, ReturnDistributionCard, BreadthBarCard,
  SentimentGaugeCard, SectorLeadersCard, LiquidityCard,
} from "../components/market/MarketWidgets";
import NewsList, { hasNewsIdentity, CATEGORY_STYLE } from "../components/common/NewsList";
import FlashPrice from "../components/common/FlashPrice";
import MarketStatusDot from "../components/common/MarketStatusDot";

const fmtTime = (d: string) => d ? new Date(d).toLocaleString("en-GB", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
const fmtNum = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const compactSar = (n: number) => {
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليار";
  if (a >= 1e6) return (n / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليون";
  return fmtNum(n);
};

/** اللغة التصميمية الموحدة للأخبار: هوية كل خبر إما شعار شركته الحقيقي أو
 * شعار الجريدة/الوكالة المصدر (من قائمة المصادر الرسمية المحقونة) — لا
 * أيقونات عامة. الخبر الذي لا يملك أياً منهما لا يُعرض في القائمة أصلاً
 * (يُكتفى به في الشريط الإخباري العلوي) — see hasNewsIdentity. */
function NewsIcon({ n, size = 40 }: { n: any; size?: number }) {
  if (n.company) return <CompanyLogo symbol={n.company} size={size} />;
  return <SourceLogo source={n.source} size={size} />;
}

function TickerCard({ variant, label, data, prefix = "" }: { variant: string; label: string; data: any; prefix?: string }) {
  const up = (data?.change_pct ?? 0) >= 0;
  return (
    <div className={`card ${variant}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="ticker-lbl" style={{color: variant === "ticker-tasi" ? "var(--pos-ink)" : variant === "ticker-brent" ? "var(--warn-ink)" : "var(--warn-ink)"}}>{label}</p>
        {/* حالة صادقة موحّدة لكلتا الشاشتين: مفتوح/مغلق/عطلة/توقف */}
        {variant === "ticker-tasi" && <MarketStatusDot withLabel market="tasi" />}
        {variant === "ticker-brent" && <MarketStatusDot withLabel market="brent" />}
      </div>
      {data?.price ? (
        <>
          <FlashPrice value={data.price} className="ticker-val">{prefix}{fmtNum(data.price)}</FlashPrice>
          <p className="ticker-ch" style={{color: up ? "var(--pos-ink)" : "var(--neg-ink)"}}>
            <span className="chg-arrow">{up ? "▲" : "▼"}</span> {(up ? "+" : "")}{fmtNum(data.change)} ({(up ? "+" : "")}{fmtNum(data.change_pct)}%)
          </p>
          {/* السيولة التقديرية أُزيلت من هنا — بطاقة «السيولة اليومية للسوق»
              تعرض الرقم الحقيقي Σ(سعر×حجم)، ولا نعرض رقمين متناقضين. */}
          {/* Reliability floor transparency: when the live source is down,
              the backend serves the last successfully fetched snapshot
              instead of an empty card — flagged honestly here rather than
              silently presented as a live quote. */}
          {data._stale_since && (
            <p className="text-[10px] text-[var(--warn-ink)] mt-1">آخر بيانات متاحة — {new Date(data._stale_since).toLocaleString("ar-SA-u-ca-gregory-nu-latn", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</p>
          )}
        </>
      ) : (
        <p className="ticker-val text-[var(--ink-muted)]">—</p>
      )}
    </div>
  );
}

/** Advancers/decliners/unchanged counts for the whole market — from the
 * twice-daily scheduled scan (see backend market_movers.py), never
 * fabricated: shows "غير متاح بعد" honestly if the job hasn't run yet. */
function MarketBreadthCard({ movers }: { movers: any }) {
  const has = movers && movers.total > 0;
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <p className="card-title">اتساع السوق</p>
        {movers?._stale_since && (
          <span className="text-[10px] text-[var(--warn-ink)]">آخر إغلاق متاح — {new Date(movers._stale_since).toLocaleDateString("ar-SA-u-ca-gregory-nu-latn", { day: "2-digit", month: "2-digit" })}</span>
        )}
      </div>
      {!has ? (
        <div className="h-16 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد — تُحدَّث تلقائياً كل ساعة خلال التداول</div>
      ) : (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-2xl font-extrabold text-[var(--pos-ink)]">{movers.advancers}</p>
            <p className="text-xs text-[var(--ink-muted)] mt-1">شركة مرتفعة</p>
          </div>
          <div>
            <p className="text-2xl font-extrabold text-[var(--neg-ink)]">{movers.decliners}</p>
            <p className="text-xs text-[var(--ink-muted)] mt-1">شركة منخفضة</p>
          </div>
          <div>
            <p className="text-2xl font-extrabold text-[var(--ink-muted)]">{movers.unchanged}</p>
            <p className="text-xs text-[var(--ink-muted)] mt-1">بلا تغيير</p>
          </div>
        </div>
      )}
    </div>
  );
}


/* ── نبض السوق: أرقامٌ أولاً، ثم جملةُ الذكاء التي تشرح السبب ─────────
   كان نصّاً واحداً يجمع ستّ معلوماتٍ بفواصل، فتختفي الأرقام في النثر
   ويتكرّر ما تعرضه البطاقات تحته. الآن تُقرأ الأرقام في لمحة، ويبقى نصّ
   الذكاء لما لا تقوله الأرقام وحدها: **سبب** الحركة من الأخبار. */
function PulseCard({ summary, tasi, brent, movers, onSearch }:
  { summary: any; tasi: any; brent: any; movers: any; onSearch?: (symbol: string) => void }) {
  const num = (v: any, d = 2) => v == null ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (v: any) => v == null ? null : (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%";
  const tone = (v: any) => v == null ? "var(--ink)" : v > 0 ? "var(--pos-ink)" : v < 0 ? "var(--neg-ink)" : "var(--ink-muted)";
  const up = movers?.advancers ?? 0, dn = movers?.decliners ?? 0;
  const breadthTotal = up + dn;
  const g = (movers?.gainers || [])[0], l = (movers?.losers || [])[0];
  const secs = (movers?.sectors || []).filter((x: any) => x?.avg_change_pct != null);
  const best = secs.length ? secs.reduce((a: any, b: any) => (a.avg_change_pct >= b.avg_change_pct ? a : b)) : null;
  const worst = secs.length ? secs.reduce((a: any, b: any) => (a.avg_change_pct <= b.avg_change_pct ? a : b)) : null;
  const phase = summary?.phase;
  const noData = tasi?.price == null && !movers?.total;

  const Cell = ({ k, v, c }: { k: string; v: any; c?: string }) => (
    <div className="min-w-0">
      <div className="text-[10px] text-[var(--ink-muted)] whitespace-nowrap">{k}</div>
      <div className="text-[12.5px] font-semibold tabular-nums truncate" style={{ color: c }} dir={typeof v === "string" && /[٠-٩0-9]/.test(v[0] || "") ? "ltr" : undefined}>{v ?? "—"}</div>
    </div>
  );

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={16} className="ai-star" />
        <h2 className="card-title">نبض السوق</h2>
        {/* ══ البحثُ حقلٌ يتمدّد في محلّه ══ (بأمر المالك · D210)
            كان زرّاً يفتح بطاقةً كاملةً فوق النبض بمربّعٍ من تصميمٍ سابق. */}
        {onSearch && <InlineStockSearch onPick={onSearch} />}
        {phase && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md"
            style={{
              background: phase === "intraday" ? "color-mix(in srgb, var(--pos-fill) 15%, transparent)"
                : phase === "pre_open" ? "color-mix(in srgb, var(--chart-1) 15%, transparent)"
                : "color-mix(in srgb, var(--ink-muted) 15%, transparent)",
              /* الحبر بدرجةٍ أعمق من صِبغته، وإلّا اختفى فيها. */
              color: phase === "intraday" ? "var(--pos-fill)" : phase === "pre_open" ? "var(--chart-1)" : "var(--ink-muted)",
            }}>
            {phase === "intraday" ? "جلسة مباشرة" : phase === "pre_open" ? "ما قبل الافتتاح" : "بعد الإغلاق"}
          </span>
        )}
        {summary?.generated_at && (
          <span className="text-[10px] text-[var(--ink-muted)] mr-auto">
            {new Date(summary.generated_at).toLocaleTimeString("ar-SA-u-ca-gregory-nu-latn", { hour: "2-digit", minute: "2-digit" })}
          </span>
        )}
      </div>

      {noData ? (
        /* الغياب حالةٌ هادئة لا نصٌّ يتظاهر بالتحليل */
        <p className="text-sm text-[var(--ink-muted)] py-2">لم تصل بيانات المؤشر بعد — تُحدَّث تلقائياً خلال التداول.</p>
      ) : (
        <>
          {/* المؤشر أولاً وأكبر */}
          <div className="flex items-baseline gap-2 mb-3">
            <span className="text-[26px] font-semibold tabular-nums" dir="ltr" style={{ color: tone(tasi?.change_pct) }}>
              {num(tasi?.price)}
            </span>
            <span className="text-[13px] font-semibold tabular-nums" dir="ltr" style={{ color: tone(tasi?.change_pct) }}>
              {pct(tasi?.change_pct) ?? ""}
            </span>
            <span className="text-[10px] text-[var(--ink-muted)]">تاسي</span>
            {/* حالة السوق (مفتوح · مغلق · عطلة · استراحة) — كانت في البطاقة
                المفردة التي حُذفت، ومكانها الطبيعي بجانب المؤشر نفسه. */}
            <span className="mr-auto"><MarketStatusDot withLabel market="tasi" tappable /></span>
          </div>

          {/* اتساع السوق شريطاً: الصورة أسرع من الجملة */}
          {breadthTotal > 0 && (
            <div className="mb-3">
              <div className="flex h-1.5 rounded-full overflow-hidden" style={{ background: "var(--hairline)" }}>
                <div style={{ width: `${up / breadthTotal * 100}%`, background: "var(--pos-fill)" }} />
                <div style={{ width: `${dn / breadthTotal * 100}%`, background: "var(--neg-fill)" }} />
              </div>
              <div className="flex justify-between text-[10.5px] mt-1.5 tabular-nums">
                <span style={{ color: "var(--pos-ink)" }}>{up} صاعدة</span>
                {movers?.sentiment?.label && <span className="text-[var(--ink-muted)]">{movers.sentiment.label}</span>}
                <span style={{ color: "var(--neg-ink)" }}>{dn} هابطة</span>
              </div>
            </div>
          )}

          {/* ثلاثة رابحين وثلاثة خاسرين بالاسم — صفٌّ لكل جانب */}
          <div className="grid grid-cols-2 gap-x-3 gap-y-2 pt-2.5" style={{ borderTop: "1px solid var(--hairline)" }}>
            <div className="min-w-0">
              <div className="text-[10px] text-[var(--ink-muted)] mb-1">أعلى الرابحين</div>
              {(movers?.gainers || []).slice(0, 3).map((x: any) => (
                <div key={x.symbol || x.name} className="flex items-center justify-between gap-2 text-[12px] leading-6">
                  <span className="truncate">{x.name}</span>
                  <span className="tabular-nums shrink-0" dir="ltr" style={{ color: tone(1) }}>
                    +{Number(x.change_pct).toFixed(2)}%
                  </span>
                </div>
              ))}
              {!(movers?.gainers || []).length && <div className="text-[12px] text-[var(--ink-muted)]">—</div>}
            </div>
            <div className="min-w-0">
              <div className="text-[10px] text-[var(--ink-muted)] mb-1">أعلى الخاسرين</div>
              {(movers?.losers || []).slice(0, 3).map((x: any) => (
                <div key={x.symbol || x.name} className="flex items-center justify-between gap-2 text-[12px] leading-6">
                  <span className="truncate">{x.name}</span>
                  <span className="tabular-nums shrink-0" dir="ltr" style={{ color: tone(-1) }}>
                    {Number(x.change_pct).toFixed(2)}%
                  </span>
                </div>
              ))}
              {!(movers?.losers || []).length && <div className="text-[12px] text-[var(--ink-muted)]">—</div>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-2.5 pt-2.5 mt-2.5" style={{ borderTop: "1px solid var(--hairline)" }}>
            <Cell k="أقوى قطاع" v={best ? `${best.sector} ${best.avg_change_pct >= 0 ? "+" : ""}${Number(best.avg_change_pct).toFixed(2)}%` : null} c={tone(best?.avg_change_pct)} />
            <Cell k="أضعف قطاع" v={worst ? `${worst.sector} ${Number(worst.avg_change_pct).toFixed(2)}%` : null} c={tone(worst?.avg_change_pct)} />
          </div>
        </>
      )}

      {/* جملة الذكاء: تشرح **السبب** من الأخبار — وهي ما لا تقوله الأرقام.
          والقاعدي احتياطٌ حين يتعذّر المزوّد، ويُعلَن المصدر في الحالتين. */}
      {summary?.summary && (
        <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--hairline)" }}>
          <div className="flex items-center gap-1.5 mb-1">
            <Brain size={13} style={{ color: "var(--brand)" }} />
            <span className="text-[11px] font-bold" style={{ color: "var(--brass)" }}>تحليل السوق</span>
            {summary?.source !== "AI" && <span className="text-[9.5px] text-[var(--ink-muted)]">(قراءة آلية)</span>}
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--ink)" }}>{summary.summary}</p>
        </div>
      )}
    </div>
  );
}

function MoversListCard({ title, rows, up }: { title: string; rows: any[]; up: boolean }) {
  // الشركة تُفتح كنافذة فوق لوحة السوق — لا إعادة تحميل للصفحة ولا فقدان مكان.
  const [sheet, setSheet] = useState<string | null>(null);
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5">
        {up ? <ArrowUp size={14} className="text-[var(--pos-ink)]" /> : <ArrowDown size={14} className="text-[var(--neg-ink)]" />}
        {title}
      </p>
      {!rows || rows.length === 0 ? (
        <div className="h-24 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد</div>
      ) : (
        <div className="space-y-1">
          {rows.map((r: any) => (
            <button key={r.symbol} onClick={() => setSheet(r.symbol)}
              className="w-full flex items-center justify-between gap-2 px-2 py-2 rounded-lg hover:bg-[var(--field)] transition-colors text-start">
              <span className="flex items-center gap-2 min-w-0">
                <CompanyLogo symbol={r.symbol} size={22} />
                <span className="text-sm text-[var(--ink)] truncate">{r.name}</span>
                <span className="tag-b shrink-0" style={{ fontSize: 10 }}>{r.symbol}</span>
              </span>
              <span className={"text-sm font-bold shrink-0 " + (up ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>
                {r.change_pct >= 0 ? "+" : ""}{r.change_pct.toFixed(2)}%
              </span>
            </button>
          ))}
        </div>
      )}
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}

const MARKET_TABS = [
  { id: "main", name: "الرئيسي", Icon: LayoutGrid },
  { id: "screener", name: "فرز السوق", Icon: SlidersHorizontal },
  { id: "news", name: "أخبار السوق", Icon: Newspaper },
  { id: "calendar", name: "مفكرة السوق", Icon: CalendarDays },
];

/** فرز السوق (نمط TradingView): فلاتر تقنية على السوق كامل — الاتجاه مقابل
 * المتوسطين (SMA50/200)، القوة النسبية RSI، القطاع، والتغيّر اليومي — مع فرز
 * قابل للنقر على الأعمدة. تُحسب المؤشرات مساءً في مسح مجدول (market_screener). */
type ScreenSort = { key: string; dir: "asc" | "desc" };

/* ── مكوّنات فرز السوق المشتركة ─────────────────────────────────────────── */

/** خيارات الترتيب على الجوال (بديل النقر على رؤوس الجدول). */
/* الحكم المركّب — يُحسب في الخادم من بياناتٍ مخزّنة (بلا أي نداء شبكة):
   التقييم مقابل **وسيط قطاع الشركة** + درجة الحوكمة. والوسوم هنا عرضٌ فقط،
   فلا يوجد تعريفان للحكم يتباعدان. */
/* ══ الحكمُ يسمّي مقياسَه ══ (بأمر المالك · D186)
   رأى المالكُ شركةً تبعد ‎40٪ عن هدف المحلّلين وحكمُها «عادل» فاستنكره —
   وهو محقٌّ في الاستنكار لا في التشخيص: الحكمُ لا يقيس هدفَ المحلّلين
   أصلاً، بل يقيس مضاعفَ الشركة على **وسيط مضاعفات قطاعها**. سؤالان
   مختلفان: «أرخصُ من أقرانه؟» و«كم يبعد عن تقدير المحلّلين؟». وقد
   يتعاكسان بحقّ: قطاعٌ كلُّه غالٍ يجعل الغاليَ «بسعر قطاعه».
   والعطبُ أن الكلمةَ كانت مطلقةً («عادل») بجوار عمود هدف المحلّلين،
   فتُقرأ حكماً على القيمة العادلة. فصارت تحمل مقياسَها في لفظها. */
const VERDICTS: Record<string, { label: string; color: string; bg: string }> = {
  cheap:        { label: "أرخص من قطاعه", color: "var(--pos-ink)", bg: "transparent" },
  fair:         { label: "بسعر قطاعه",    color: "var(--ink-muted)", bg: "transparent" },
  expensive:    { label: "أغلى من قطاعه", color: "var(--neg-ink)", bg: "transparent" },
  loss:         { label: "خاسرة",         color: "var(--neg-ink)", bg: "transparent" },
  insufficient: { label: "لا يكفي",       color: "var(--ink-muted)", bg: "transparent" },
};

/* الحالات القابلة للبحث ثلاث فقط. «خاسرة» و«لا يكفي» بيانُ حالٍ لا خيارُ بحث،
   و«مبخّس وسليم» لم يكن حكماً مستقلّاً بل حاصلَ ضرب التقييم في السلامة —
   وللسلامة فلترها المستقلّ، فتقاطعهما يغني عن تصنيفٍ يضاعف القائمة. */
const VERDICT_FILTERS = ["cheap", "fair", "expensive"] as const;

const VerdictTag = ({ v, small = false, gap, basis }:
  { v?: string; small?: boolean; gap?: number | null; basis?: string | null }) => {
  const d = VERDICTS[v || ""];
  if (!d) return null;
  /* التلميحةُ تقول الأساسَ والرقم: مكرّرُ الربحية أم مكرّرُ الدفترية، وكم
     الفجوة — فلا يبقى الحكمُ كلمةً بلا سند. */
  const title = gap != null
    ? `مقابل وسيط ${basis === "pb" ? "مكرّر الدفترية" : "مكرّر الربحية"} للقطاع: `
      + `${gap > 0 ? "أرخص بـ" : "أغلى بـ"}${Math.abs(gap).toFixed(1)}%`
    : "مقابل وسيط مضاعفات القطاع";
  return (
    <span className="rounded shrink-0 whitespace-nowrap" title={title}
      style={{ color: d.color, background: d.bg, border: `1px solid ${d.color}33`,
               fontSize: small ? 9.5 : 10.5, padding: small ? "1px 5px" : "2px 6px" }}>
      {d.label}
    </span>
  );
};

const SORT_OPTS: [string, string][] = [
  ["upside_pct", "الفرق عن هدف المحللين"],
  ["value_gap_pct", "الفجوة عن القطاع"],
  ["dividend_yield", "عائد التوزيعات"],
  ["change_pct", "التغيّر اليومي"],
  ["price", "السعر"],
  ["dist_sma50", "البُعد عن م50"],
  ["dist_sma200", "البُعد عن م200"],
  ["rsi", "RSI"],
  ["finance_score", "درجة السلامة"],
  ["pe_ratio", "مضاعف الربحية"],
];

/** الفاصل الزمني — يحكم كل المقاييس التقنية (م50/م200/الاتجاه/RSI/ماكد). */
function FrameSeg({ frame, setFrame }: { frame: string; setFrame: (v: any) => void }) {
  return (
    <div className="seg inline-flex shrink-0">
      {([["D", "يومي"], ["W", "أسبوعي"], ["M", "شهري"]] as [string, string][]).map(([k, lbl]) => (
        <button key={k} onClick={() => setFrame(k)} aria-pressed={frame === k}
          className={"seg-btn" + (frame === k ? " on" : "")}>
          {lbl}
        </button>
      ))}
    </div>
  );
}

/** خانة مقياس داخل بطاقة الجوال — عنوان صغير فوق قيمة بارزة. */
function Metric({ label, value, color }: { label: string; value: string | null; color?: string }) {
  return (
    <div className="text-center">
      <div className="text-[9.5px] text-[var(--ink-muted)] mb-0.5">{label}</div>
      {/* dir="ltr" على الرقم: بدونه تُدفع إشارة السالب إلى آخر النصّ في سياقٍ
          عربي فيُقرأ «50%-» بدل «-50%» — ويلتبس بالموجب عند المرور السريع. */}
      <div className="text-[12px] font-bold tabular-nums" dir="ltr"
        style={{ color: value == null ? "var(--ink-muted)" : (color || "var(--ink)") }}>
        {value ?? "—"}
      </div>
    </div>
  );
}

/** وسم صغير ملوّن — لا يظهر إلا حين تتوفّر البيانة فعلاً. */
function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md whitespace-nowrap"
      style={{ color, background: `${color}1a`, border: `1px solid ${color}33` }}>
      {text}
    </span>
  );
}


/** مجموعة فلاتر داخل اللوحة — عنوان صغير ثم محتواها، بمساحة تنفّس. */
function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-bold text-[var(--ink-muted)] mb-2">{title}</div>
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

/** صفّ داخل اللوحة: التسمية يميناً والتحكّم يساراً. */
function SheetRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[12px] text-[var(--ink)]">{label}</span>
      <div className="shrink-0">{children}</div>
    </div>
  );
}


/* ── التحليل القطاعي ───────────────────────────────────────────────────────
   أداء كل قطاع عبر فترات (٣ش…٥س) + متوسط عائد توزيعاته — لقياس أين ينمو
   رأس المال فعلاً. الوسيط لا المتوسط، كي لا تُشوّه شركةٌ شاذّة صورة القطاع. */
const SECTOR_PERIODS: [string, string][] = [
  ["3m", "3 أشهر"], ["6m", "6 أشهر"], ["1y", "سنة"], ["3y", "3 سنوات"], ["5y", "5 سنوات"],
];

function SectorAnalysis({ sortKey: sortKeyProp, onSort }:
  { sortKey?: string; onSort?: (k: string) => void }) {
  const { data: rows = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["sector-analysis"],
    queryFn: () => marketApi.sectors().then(r => Array.isArray(r.data.data) ? r.data.data : []),
    staleTime: 30 * 60 * 1000,
  });
  /* ══ الترتيبُ يُملى من الشريط لا يُرسم هنا ══ (بأمر المالك · D193)
     كان صفّاً مستقلاً بإطارٍ وحشوٍ وخلفيةٍ زرقاءَ ثابتة — تصميمٌ سابقٌ لا
     يشبه مبدّلات التطبيق، ويجلس تحت شريط الأدوات فيصير للشاشة صفّان
     يفعلان الشيءَ نفسه. فصعِد إلى الشريط نفسِه، في موضع مربّع البحث من
     تبويب الأسهم — صفٌّ واحدٌ لكلّ ما يضبط العرض. */
  const sortKey = sortKeyProp || "1y";
  /* رأسُ الجدول يبقى مرتّباً: الحالةُ في الشريط، والنداءُ يصعد إليها.
     كان يُنادى `setSortKey` بعد أن رُفعت الحالة — اسمٌ لا وجودَ له،
     يُسقط تبويبَ القطاعات كلَّه عند أوّل رسم (D211). */
  const setSortKey = (k: string) => onSort?.(k);

  const sorted = React.useMemo(() => {
    return [...rows].sort((a: any, b: any) => {
      const av = a[sortKey], bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return bv - av;
    });
  }, [rows, sortKey]);

  const col = (v: any) => v == null ? "var(--ink-muted)" : v >= 0 ? "var(--pos-ink)" : "var(--neg-ink)";
  const val = (v: any) => v == null ? "—" : `${v >= 0 ? "+" : ""}${v}%`;

  if (isLoading) return <div className="space-y-2">{[...Array(6)].map((_, i) => <div key={i} className="h-10 skeleton rounded-lg" />)}</div>;
  if (isError) return (
    <div className="py-12 text-center text-sm" style={{ color: "var(--neg-ink)" }}>
      تعذّر جلب التحليل القطاعي.
      <button onClick={() => refetch()} className="underline mr-2" style={{ color: "var(--ink-muted)" }}>إعادة المحاولة</button>
    </div>
  );
  if (!rows.length) return <div className="py-12 text-center text-[var(--ink-muted)] text-sm">لم يُحسب التحليل القطاعي بعد — يُبنى مساءً بعد إغلاق تداول.</div>;

  return (
    <div>
      {/* الجوال: بطاقات */}
      <div className="md:hidden space-y-2">
        {sorted.map((r: any) => (
          <div key={r.sector} className="rounded-2xl p-3" style={{ background: "var(--pop)", border: "1px solid var(--line)" }}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[var(--ink)] text-[13px] font-bold truncate">{r.sector}</span>
              <span className="text-[10px] text-[var(--ink-muted)] shrink-0">{r.companies} شركة</span>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2.5" style={{ borderTop: "1px solid var(--line)" }}>
              {SECTOR_PERIODS.slice(0, 3).map(([k, lbl]) => (
                <Metric key={k} label={lbl} value={r[k] == null ? null : val(r[k])} color={col(r[k])} />
              ))}
            </div>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {SECTOR_PERIODS.slice(3).map(([k, lbl]) => (
                <Metric key={k} label={lbl} value={r[k] == null ? null : val(r[k])} color={col(r[k])} />
              ))}
              <Metric label="التوزيعات" value={r.dividend_yield == null ? null : `${r.dividend_yield}%`} color="var(--info-ink)" />
            </div>
          </div>
        ))}
      </div>

      {/* الكمبيوتر: جدول */}
      <div className="hidden md:block overflow-x-auto -mx-1">
        <table className="w-full text-[12px] tabular-nums">
          <thead>
            <tr className="text-start" style={{ borderBottom: "1px solid var(--hairline)" }}>
              <th className="px-2 py-2 text-[var(--ink-muted)] font-semibold text-start">القطاع</th>
              {SECTOR_PERIODS.map(([k, lbl]) => (
                <th key={k} onClick={() => setSortKey(k)}
                  className="px-2 py-2 text-[var(--ink-muted)] font-semibold cursor-pointer select-none whitespace-nowrap">
                  {lbl}{sortKey === k && <span className="text-[var(--brand-ink)]"> ▾</span>}
                </th>
              ))}
              <th onClick={() => setSortKey("dividend_yield")}
                className="px-2 py-2 text-[var(--ink-muted)] font-semibold cursor-pointer select-none whitespace-nowrap">
                التوزيعات{sortKey === "dividend_yield" && <span className="text-[var(--brand-ink)]"> ▾</span>}
              </th>
              <th className="px-2 py-2 text-[var(--ink-muted)] font-semibold">شركات</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r: any) => (
              <tr key={r.sector} style={{ borderBottom: "1px solid var(--hairline)" }}>
                <td className="px-2 py-2 text-[var(--ink)] font-semibold">{r.sector}</td>
                {SECTOR_PERIODS.map(([k]) => (
                  <td key={k} className="px-2 py-2 tabular-nums font-bold" style={{ color: col(r[k]) }}>{val(r[k])}</td>
                ))}
                <td className="px-2 py-2 tabular-nums" style={{ color: r.dividend_yield == null ? "var(--ink-muted)" : "var(--info-ink)" }}>
                  {r.dividend_yield == null ? "—" : `${r.dividend_yield}%`}
                </td>
                <td className="px-2 py-2 text-[var(--ink-muted)] tabular-nums">{r.companies}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10.5px] text-[var(--ink-muted)] mt-3 pt-2.5 text-center" style={{ borderTop: "1px solid var(--line)" }}>
        وسيط عائد شركات كل قطاع لكل فترة — الفترة التي لا يبلغها تاريخ شركاته تظهر «—»
      </p>
    </div>
  );
}

function ScreenerTab({ onOpen }: { onOpen: (symbol: string) => void }) {
  /* الخادم يعيد الآن {rows, state} ويبني المسح في الخلفية بدل أن يحسبه داخل
     الطلب. نقبل الشكلين (قائمة صِرفة أو غلاف) حتى لا تنكسر واجهةٌ أمام خادمٍ
     أقدم، ونعيد السؤال كل عشر ثوانٍ ما دام البناء جارياً — بحالةٍ معلنة لا
     هيكلٍ صامت. */
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["screener"],
    queryFn: () => marketApi.screener().then(r => {
      const d = r.data.data;
      if (Array.isArray(d)) return { rows: d, state: "ready" as const };
      return { rows: Array.isArray(d?.rows) ? d.rows : [], state: (d?.state || "ready") as "ready" | "building" };
    }),
    staleTime: 30 * 60 * 1000,
    retry: 1,
    refetchInterval: q => (q.state.data as any)?.state === "building" ? 10000 : false,
  });
  const rows = data?.rows ?? [];
  const building = data?.state === "building";

  const [q, setQ] = useState("");
  const [sector, setSector] = useState("");
  const [frame, setFrame] = useState<"D" | "W" | "M">("D");   // الفاصل الزمني
  const [ma50, setMa50] = useState<"" | "above" | "below">("");
  const [ma200, setMa200] = useState<"" | "above" | "below">("");
  const [trend, setTrend] = useState<"" | "golden" | "death">("");
  /* طيُّ الفلاتر على الكمبيوتر — يُحفظ: من يفتحها دائماً لا يُجبَر على
     فتحها كل مرّة، ومن يريد الشاشة للنتائج لا تُفرَض عليه. */
  const [deskFilters, setDeskFilters] = useState<boolean>(
    () => localStorage.getItem("screener:filters") === "1");

  /* ══ عرضُ زرّ الفلاتر = عرضُ المبدّل فوقه ══
     العمود الأيسر يجب أن يقف على خطٍّ واحد: المبدّل في الصفّ الأعلى وزرّ
     الفلاتر تحته. وتثبيت رقمٍ يكسر ذلك أول ما يتغيّر نصٌّ أو خطّ أو لغة —
     فيُقاس النظير نفسه ويُنسخ عرضه، وتُراقَب تغيّراته فيبقى التطابق حيّاً
     لا لحظياً. */
  const viewSegRef = React.useRef<HTMLDivElement | null>(null);
  const [segW, setSegW] = useState<number | null>(null);
  /* المطابقة في العرض قاعدةُ كمبيوتر: على الجوّال العرض ضيّق والصفّ يحمل
     عنصرين، ففرضُ عرضٍ منسوخ يزحمهما ويقذف أحدهما خارج الحافّة — وهو ما
     وقع فعلاً وقِيس في اللقطة. */
  const [isDesk, setIsDesk] = useState<boolean>(
    () => typeof window !== "undefined" && window.innerWidth >= 768);
  React.useEffect(() => {
    const m = window.matchMedia("(min-width: 768px)");
    const on = () => setIsDesk(m.matches);
    m.addEventListener("change", on); on();
    return () => m.removeEventListener("change", on);
  }, []);
  React.useLayoutEffect(() => {
    const el = viewSegRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => setSegW(Math.round(el.getBoundingClientRect().width)));
    ro.observe(el);
    setSegW(Math.round(el.getBoundingClientRect().width));
    return () => ro.disconnect();
  }, []);
  useEffect(() => { localStorage.setItem("screener:filters", deskFilters ? "1" : "0"); }, [deskFilters]);
  const [rsiBand, setRsiBand] = useState<"" | "oversold" | "neutral" | "overbought">("");
  const [macd, setMacd] = useState<"" | "up" | "down" | "bull" | "bear">("");
  // فلاتر أساسية/شرعية (من بيانات التطبيق نفسه — لا نداءات إضافية)
  const [sharia, setSharia] = useState<"" | "COMPLIANT">("");
  const [minYield, setMinYield] = useState("");
  const [minScore, setMinScore] = useState("");
  // التقييم النسبي: فجوة السعر عن وسيط القطاع + الحكم المركّب.
  const [minGap, setMinGap] = useState("");
  // الفرق عن القيمة العادلة (تقدير المحللين) — مقياسٌ ثانٍ مستقلّ عن القطاع.
  const [minUpside, setMinUpside] = useState("");
  const [verdict, setVerdict] = useState("");
  // الافتراضي: عائد التوزيعات تنازلياً — سؤال المستثمر الأول في هذا التطبيق.
  const [sort, setSort] = useState<ScreenSort>({ key: "dividend_yield", dir: "desc" });
  const [sheet, setSheet] = useState(false);   // لوحة الفلاتر السفلية (جوال)
  const [view, setView] = useState<"stocks" | "sectors">("stocks");  // أسهم | قطاعات
  /* ترتيبُ القطاعات يسكن هنا لا في المكوّن: مبدّلُه في الشريط والقائمةُ
     تحته، فلا يملك أحدُهما الحالةَ دون الآخر. */
  const [secSort, setSecSort] = useState<string>("1y");

  // القطاعات من الدليل المعتمد (٢٢ قطاعاً) لا من صفوف الفرز — فالقائمة تكتمل
  // دائماً حتى قبل حساب الفرز، وتتّسق مع بقية أقسام التطبيق. نضمّ أي قطاع
  // يظهر في البيانات ولم يرد في الدليل (احتياط ضد انحراف مستقبلي).
  const sectors = React.useMemo(() => {
    const fromRows = rows.map((r: any) => r.sector).filter(Boolean) as string[];
    return Array.from(new Set([...SECTORS, ...fromRows]))
      .sort((a, b) => a.localeCompare(b, "ar"));
  }, [rows]);

  /** مقاييس الصفّ حسب الفاصل المختار (يومي/أسبوعي/شهري). */
  const M = React.useCallback((r: any) => (r.frames?.[frame] ?? (frame === "D" ? r : {})), [frame]);

  const filtered = React.useMemo(() => {
    const term = q.trim().toLowerCase();
    const yMin = parseFloat(minYield), sMin = parseFloat(minScore), gMin = parseFloat(minGap);
    const uMin = parseFloat(minUpside);
    let list = rows.filter((r: any) => {
      if (term && !(`${r.name}`.toLowerCase().includes(term) || `${r.symbol}`.includes(term))) return false;
      if (sector && r.sector !== sector) return false;
      const m = M(r);
      // أعلام ثلاثية الحالة: null = «غير متاح» (لا متوسط بعد) → تُستثنى من
      // فلتري «فوق/تحت» بدل أن تُحسب كذباً ضمن «تحت» كما كان سابقاً.
      if (ma50 === "above" && m.above_sma50 !== true) return false;
      if (ma50 === "below" && m.above_sma50 !== false) return false;
      if (ma200 === "above" && m.above_sma200 !== true) return false;
      if (ma200 === "below" && m.above_sma200 !== false) return false;
      if (trend === "golden" && m.golden_cross !== true) return false;
      if (trend === "death" && m.golden_cross !== false) return false;
      if (rsiBand) {
        const v = m.rsi;
        if (v == null) return false;
        if (rsiBand === "oversold" && v >= 30) return false;
        if (rsiBand === "overbought" && v <= 70) return false;
        if (rsiBand === "neutral" && (v < 30 || v > 70)) return false;
      }
      // ماكد: تقاطع طازج (صاعد/هابط) أو الحالة العامة فوق/تحت خط الإشارة.
      if (macd === "up" && m.macd_cross !== "up") return false;
      if (macd === "down" && m.macd_cross !== "down") return false;
      if (macd === "bull" && m.macd_bullish !== true) return false;
      if (macd === "bear" && m.macd_bullish !== false) return false;
      if (sharia && r.sharia !== sharia) return false;
      if (!isNaN(yMin) && !(r.dividend_yield != null && r.dividend_yield >= yMin)) return false;
      if (!isNaN(sMin) && !(r.finance_score != null && r.finance_score >= sMin)) return false;
      if (!isNaN(gMin) && !(r.value_gap_pct != null && r.value_gap_pct >= gMin)) return false;
      if (!isNaN(uMin) && !(r.upside_pct != null && r.upside_pct >= uMin)) return false;
      if (verdict && r.verdict !== verdict) return false;
      return true;
    });
    const { key, dir } = sort;
    // مفاتيح الفرز التقنية تتبع الفاصل المختار؛ البقية من جذر الصفّ.
    const TF = new Set(["rsi", "dist_sma50", "dist_sma200", "sma50", "sma200"]);
    const val = (r: any, k: string) => (TF.has(k) ? M(r)[k] : r[k]);
    list = [...list].sort((a: any, b: any) => {
      const av = val(a, key), bv = val(b, key);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return dir === "asc" ? av - bv : bv - av;
    });
    return list;
  }, [rows, q, sector, frame, M, ma50, ma200, trend, rsiBand, macd, sharia, minYield, minScore, minGap, minUpside, verdict, sort]);

  /* حدّ العرض ٢٠٠ صفّاً — لأداء الصفحة. لكنه كان **صامتاً**: لو طابقت فلاترك
     ٢٣٠ شركة رأيتَ ٢٠٠ وظننتَ أن الباقي غير موجود، بلا أي إشارة. الآن يُعرض
     العدد الكلي دائماً، ويظهر تنبيهٌ صريح حين يُقتطع شيء فعلاً. */
  const ROW_CAP = 200;
  const shown = filtered.slice(0, ROW_CAP);
  const hidden = Math.max(0, filtered.length - shown.length);

  /* الجوّال يبني ثلاثين بطاقة أولاً ثم يزيد بالطلب: البطاقة الواحدة تحوي
     شريطين وأربعة وسوم، فبناء مئتين دفعةً واحدة يؤخّر أول رسمةٍ على الهاتف
     بلا أن يقرأ أحدٌ الصفّ المئة. والفلاتر تُعيده إلى ثلاثين كي لا تبدأ
     نتيجةٌ جديدة من منتصف قائمةٍ قديمة. */
  const MOBILE_PAGE = 30;
  const [mobileCount, setMobileCount] = useState(MOBILE_PAGE);
  useEffect(() => { setMobileCount(MOBILE_PAGE); }, [q, sector, ma50, ma200, trend, rsiBand, macd, sharia, minYield, minScore, minGap, minUpside, verdict, sort.key, sort.dir]);
  const shownMobile = shown.slice(0, mobileCount);

  const reset = () => {
    setQ(""); setSector(""); setMa50(""); setMa200(""); setTrend(""); setRsiBand(""); setMacd("");
    setSharia(""); setMinYield(""); setMinScore(""); setMinGap(""); setMinUpside(""); setVerdict("");
  };
  const activeCount = [sector, ma50, ma200, trend, rsiBand, macd, sharia, minYield.trim(), minScore.trim(),
                       minGap.trim(), minUpside.trim(), verdict]
    .filter(Boolean).length + (q.trim() ? 1 : 0);

  /* مبدّلاتُ الفلاتر بلغة `.seg` نفسِها — كانت بخلفيةٍ زرقاءَ ثابتة
     وخيوطٍ فاصلة، تصميمٌ سابقٌ لم يلحقه التوحيد (D202). والسلوكُ كما هو:
     الضغطُ على المختار يُلغيه. */
  const Seg = ({ value, set, opts }: { value: string; set: (v: any) => void; opts: [string, string][] }) => (
    <div className="seg inline-flex w-fit">
      {opts.map(([k, lbl]) => (
        <button key={k} onClick={() => set(value === k ? "" : k)} aria-pressed={value === k}
          className={"seg-btn whitespace-nowrap" + (value === k ? " on" : "")}>
          {lbl}
        </button>
      ))}
    </div>
  );

  const th = (key: string, label: string) => (
    <th className="px-2 py-2 text-[var(--ink-muted)] font-semibold cursor-pointer select-none whitespace-nowrap"
      onClick={() => setSort(s => ({ key, dir: s.key === key && s.dir === "desc" ? "asc" : "desc" }))}>
      <span className="inline-flex items-center gap-0.5">
        {label}
        {sort.key === key && <span className="text-[var(--brand-ink)]">{sort.dir === "desc" ? "▾" : "▴"}</span>}
      </span>
    </th>
  );

  const fmt = (v: any, d = 2) => v == null ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal size={16} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">فرز السوق</h2>
        {view === "stocks" && <span className="text-[11px] ms-auto" style={{ color: "var(--ink-muted)" }}>{filtered.length} من {rows.length}</span>}
      </div>

      {/* مبدّل العرض: الأسهم | القطاعات — **خارج الشرط دائماً**.
          كان له نسختان: واحدةٌ هنا للكمبيوتر وحده، وأخرى داخل شريط أدوات
          الفرز. وشريط الأدوات كلّه يختفي عند اختيار «القطاعات»، فيختفي معه
          المبدّل الوحيد الظاهر على الجوّال — فلا سبيل للرجوع إلى «الأسهم»
          إلا بإعادة تحميل الصفحة. هذا هو «التعليق» الذي وصفه المالك.
          الآن مبدّلٌ واحد، ظاهرٌ في كل المقاسات، خارج ما يُستبدل. */}
      {/* ══ الصفّ الأول: البحث يمتدّ من أقصى اليمين، والمبدّل عند أقصى اليسار ══
          الاتساق قاعدةٌ لا ذوق: كل صفٍّ يبدأ من اليمين وينتهي عند اليسار،
          وأطرافُه محاذيةٌ لأطراف الصفّ الذي تحته. فالعين تمسح عموداً واحداً
          لا سلّماً متعرّجاً. */}
      {/* الترتيب واحدٌ في المقاسين بأمر المالك: البحث يميناً والمبدّل
          يساراً. والفرق مقاساتٌ لا بنية — الحشوة والخطّ يصغران على الجوّال
          (قاعدة `.seg-btn` المتجاوبة) فيتّسع الصفّ بلا قصّ ولا خروج. */}
      <div className="flex items-center gap-2 mb-2.5">
        {/* إطارٌ واحد لكل ما في الشريط: نفس الخيط (--field-line) ونفس
            الاستدارة (١٠) ونفس الارتفاع (٣٤). كان البحث والفلاتر يأخذان
            الخيط الشعري واستدارةً أوسع، فيبدوان أخفّ من المبدّلات بجوارهما
            — وهو اختلافٌ يُرى ولا يُفسَّر.
            والتعليق فوق الشرط لا داخله: موضعُ التعبير في JSX لا يقبل
            تعليقاً، وهو خطأٌ وقعتُ فيه قبلُ فأعادني إليه التسرّع. */}
        {view === "stocks" ? (
          <div className="flex-1 min-w-0 flex items-center gap-2 px-3"
            style={{ border: "1px solid var(--field-line)", borderRadius: 10, height: 34, background: "var(--bg)" }}>
            <Search size={14} className="text-[var(--ink-muted)] shrink-0" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="بحث بالاسم أو الرمز"
              className="flex-1 min-w-0 bg-transparent text-[13px] text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:outline-none" />
          </div>
        ) : (
          /* في وضع القطاعات: ترتيبُها بلغة المبدّلات نفسِها وفي موضع البحث. */
          <div className="flex-1 min-w-0 flex items-center gap-2 overflow-x-auto">
            <span className="text-[10px] text-[var(--ink-muted)] shrink-0">رتّب حسب</span>
            <div className="seg inline-flex w-fit shrink-0">
              {[...SECTOR_PERIODS, ["dividend_yield", "التوزيعات"] as [string, string]].map(([k, lbl]) => (
                <button key={k} onClick={() => setSecSort(k)} aria-pressed={secSort === k}
                  className={"seg-btn whitespace-nowrap" + (secSort === k ? " on" : "")}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>
        )}
        <div ref={viewSegRef} className="seg inline-flex w-fit shrink-0">
          {([["stocks", "الأسهم"], ["sectors", "القطاعات"]] as [any, string][]).map(([k, lbl]) => (
            <button key={k} onClick={() => setView(k)} aria-pressed={view === k}
              className={"seg-btn" + (view === k ? " on" : "")}>
              {lbl}
            </button>
          ))}
        </div>
      </div>

      {view === "sectors" ? <SectorAnalysis sortKey={secSort} onSort={setSecSort} /> : (<>

      {/* ══ أدوات الفرز ══
          الجوال: البحث والفاصل ظاهران دائماً (الأكثر استخداماً)، وبقيّة
          الفلاتر تُطوى في لوحة سفلية مجمّعة — بدل جدارٍ من الأزرار المتكدّسة.
          الكمبيوتر: الفلاتر مبسوطة (المساحة تسمح). */}
      <div className="space-y-2.5 mb-4">
        {/* ══ الصفّ الثاني: ثلاثة مواضع ثابتة ══
            الفاصل الزمني يميناً · القطاعات وسطاً · الفلاتر يساراً. المواضع
            ثابتةٌ لا تتبع طول المحتوى، فلا يزحف عنصرٌ حين يطول اسم قطاع.
            وثلاثة أعمدةٍ متساوية تضمن أن يقف الأوسط في الوسط حقيقةً — لا
            «بين الاثنين» كما يفعل التوزيع بالمسافات. */}
        <div className="grid grid-cols-3 items-center gap-2">
          <div className="min-w-0 justify-self-start"><FrameSeg frame={frame} setFrame={setFrame} /></div>

          {/* القطاعات بإطار المبدّلات نفسه — كان صندوقاً بحوافَّ أخرى
              وارتفاعٍ أخفض، فيبدو غريباً بين نظيريه. */}
          <div className="min-w-0 justify-self-center seg inline-flex w-fit max-w-full">
            <select value={sector} onChange={e => setSector(e.target.value)}
              className="seg-btn bg-transparent focus:outline-none truncate"
              style={{ fontWeight: sector ? 800 : 400, color: sector ? "var(--ink)" : "var(--ink-muted)" }}>
              <option value="">كل القطاعات</option>
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="min-w-0 justify-self-end flex items-center gap-2">
            {activeCount > 0 && (
              <button onClick={reset} className="text-[11px] text-[var(--neg-ink)] px-1">مسح</button>
            )}
            <button onClick={() => { if (window.innerWidth < 768) setSheet(true); else setDeskFilters(v => !v); }}
              className="flex items-center gap-1.5 px-3 text-[11px] text-[var(--ink)]"
              style={{ border: "1px solid transparent", borderRadius: 10, height: 34,
                       background: "var(--bg)", fontWeight: deskFilters || activeCount ? 800 : 400,
                       // عرضُ المبدّل فوقه — يُقاس لا يُثبَّت. والتوسيط داخله
                       // لأن العرض صار مفروضاً من الخارج لا من المحتوى.
                       width: segW ?? undefined, justifyContent: "center" }}
              aria-expanded={deskFilters}>
              <SlidersHorizontal size={13} />
              الفلاتر
              {activeCount > 0 && (
                <span className="min-w-[16px] h-[16px] px-1 rounded-full text-[9.5px] font-bold flex items-center justify-center"
                  style={{ background: "var(--ink)", color: "var(--bg)" }}>{activeCount}</span>
              )}
              <ChevronDown size={13} className={"hidden md:block transition-transform " + (deskFilters ? "rotate-180" : "")} />
            </button>
          </div>
        </div>

        {/* ══ الفلاتر — كمبيوتر ══
            كانت مبسوطةً دائماً: جدارٌ من عشر مجموعاتٍ بتسمياتٍ صغيرة
            متناثرة، تسبق النتائج وتزاحمها. والفرز يُستعمل بفلترٍ أو
            فلترين، ثم يُقرأ الجدول طويلاً — فالجدار يشغل الشاشة لأجل
            لحظةٍ ويُعيق ما بعدها.

            الآن: زرٌّ واحد يفتحها، وثلاث مجموعاتٍ مسمّاة بدل التناثر —
            الاتجاه الفنّي · الجودة والقيمة · التوافق والحكم. والافتراضيّ
            مطويّ، فالشاشة للنتائج. وعدد الفلاتر النشطة على الزرّ فلا
            يُنسى فلترٌ يُقصي شركاتٍ بلا أن يُرى. */}
        {/* الزرّ نفسه صار في الصفّ الثاني — تكراره هنا يُعيد عطب «زرّين
            لوظيفةٍ واحدة» الذي عولج للتوّ. هنا اللوحة وحدها. */}
        <div className="hidden md:block">
          {deskFilters && (
            <div className="mt-2.5 rounded-xl border border-[var(--hairline)] p-3 space-y-3">
              <div>
                <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">الاتجاه الفنّي</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-[var(--ink-muted)]">السعر فوق متوسّط ٥٠</span>
                  <Seg value={ma50} set={setMa50} opts={[["above", "فوق"], ["below", "تحت"]]} />
                  <span className="text-[10px] text-[var(--ink-muted)]">فوق متوسّط ٢٠٠</span>
                  <Seg value={ma200} set={setMa200} opts={[["above", "فوق"], ["below", "تحت"]]} />
                  {/* المصطلح مشروحٌ في مكانه لا في حاشيةٍ أسفل الشاشة. */}
                  <span className="text-[10px] text-[var(--ink-muted)]" title="متوسّط ٥٠ يوماً مقابل متوسّط ٢٠٠ يوم">
                    تقاطع المتوسّطين
                  </span>
                  <Seg value={trend} set={setTrend} opts={[["golden", "صاعد"], ["death", "هابط"]]} />
                  <span className="text-[10px] text-[var(--ink-muted)]">قوّة نسبية</span>
                  <Seg value={rsiBand} set={setRsiBand} opts={[["oversold", "تشبّع بيعي"], ["neutral", "محايد"], ["overbought", "تشبّع شرائي"]]} />
                  <span className="text-[10px] text-[var(--ink-muted)]">ماكد</span>
                  <Seg value={macd} set={setMacd} opts={[["up", "تقاطع صاعد"], ["down", "تقاطع هابط"], ["bull", "فوق الإشارة"], ["bear", "تحت الإشارة"]]} />
                </div>
              </div>

              <div className="pt-2.5 border-t border-[var(--hairline)]">
                <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">الجودة والقيمة</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-[var(--ink-muted)]">التوزيعات ≥</span>
                  <input value={minYield} onChange={e => setMinYield(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-16 border border-[var(--hairline)] rounded-lg px-2 py-1 text-[12px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]"
                    style={{ background: "var(--field)" }} />
                  <span className="text-[10px] text-[var(--ink-muted)]">درجة السلامة ≥</span>
                  <input value={minScore} onChange={e => setMinScore(e.target.value)} inputMode="decimal" placeholder="0-100"
                    className="w-20 border border-[var(--hairline)] rounded-lg px-2 py-1 text-[12px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]"
                    style={{ background: "var(--field)" }} />
                  <span className="text-[10px] text-[var(--ink-muted)]">أرخص من قطاعه ≥</span>
                  <input value={minGap} onChange={e => setMinGap(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-16 border border-[var(--hairline)] rounded-lg px-2 py-1 text-[12px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]"
                    style={{ background: "var(--field)" }} />
                  <span className="text-[10px] text-[var(--ink-muted)]">تحت هدف المحللين ≥</span>
                  <input value={minUpside} onChange={e => setMinUpside(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-16 border border-[var(--hairline)] rounded-lg px-2 py-1 text-[12px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]"
                    style={{ background: "var(--field)" }} />
                </div>
              </div>

              <div className="pt-2.5 border-t border-[var(--hairline)]">
                <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">التوافق والحكم</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-[var(--ink-muted)]">شرعي</span>
                  <Seg value={sharia} set={setSharia} opts={[["COMPLIANT", "متوافق"]]} />
                  <span className="text-[10px] text-[var(--ink-muted)]">مقابل القطاع</span>
                  <select value={verdict} onChange={e => setVerdict(e.target.value)}
                    className="border border-[var(--hairline)] rounded-lg px-2 py-1 text-[12px] text-[var(--ink)] focus:outline-none"
                    style={{ background: "var(--field)" }}>
                    <option value="">الكل</option>
                    {VERDICT_FILTERS.map(k => <option key={k} value={k}>{VERDICTS[k].label}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(6)].map((_, i) => <div key={i} className="h-10 skeleton" />)}</div>
      ) : isError ? (
        /* خطأٌ صريح لا هيكلٌ أبدي — ومعه طريق الخروج. */
        <div className="py-12 text-center text-sm" style={{ color: "var(--neg-ink)" }}>
          تعذّر جلب الفرز.
          <button onClick={() => refetch()} className="underline mr-2" style={{ color: "var(--ink-muted)" }}>إعادة المحاولة</button>
        </div>
      ) : building ? (
        <div className="py-12 text-center text-[var(--ink-muted)] text-sm">
          يُبنى مسح السوق الآن — يظهر تلقائياً عند اكتماله{isFetching ? "…" : ""}
        </div>
      ) : rows.length === 0 ? (
        <div className="py-12 text-center text-[var(--ink-muted)] text-sm">لم يُحسب الفرز بعد — يُبنى مساءً بعد إغلاق تداول.</div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-[var(--ink-muted)] text-sm">لا نتائج مطابقة للفلاتر الحالية.</div>
      ) : (
        <>
        {/* ══ الجوال: بطاقة لكل شركة ══
            تسلسل بصري: الهوية والسعر (الأهمّ) ← ثلاثية تقنية ← وسوم البيانات
            المتاحة فقط. لا جدول أفقي يُجبر المستخدم على السحب. */}
        <div className="md:hidden space-y-2">
          {shownMobile.map((r: any) => {
            const m = M(r);
            const up = (r.change_pct ?? 0) >= 0;
            return (
              <button key={r.symbol} onClick={() => onOpen(r.symbol)}
                className="w-full text-start rounded-2xl p-3 active:scale-[.99] transition-transform"
                style={{ background: "var(--pop)", border: "1px solid var(--line)" }}>
                {/* الهوية + السعر */}
                <div className="flex items-center gap-2.5">
                  <CompanyLogo symbol={r.symbol} size={34} />
                  <div className="min-w-0 flex-1">
                    <div className="text-[var(--ink)] text-[13px] font-bold truncate">{r.name}</div>
                    <div className="text-[10px] text-[var(--ink-muted)] truncate">{r.symbol}{r.sector ? ` · ${r.sector}` : ""}</div>
                  </div>
                  <div className="text-end shrink-0">
                    <div className="text-[var(--ink)] font-bold tabular-nums text-[15px]">{fmt(r.price)}</div>
                    <div className="text-[11px] font-bold tabular-nums"
                      style={{ color: r.change_pct == null ? "var(--ink-muted)" : up ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                      {r.change_pct == null ? "—" : (<><span className="chg-arrow">{up ? "▲" : "▼"}</span> {up ? "+" : ""}{r.change_pct.toFixed(2)}%</>)}
                    </div>
                  </div>
                </div>

                {/* الثلاثية التقنية للفاصل المختار */}
                <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2.5" style={{ borderTop: "1px solid var(--line)" }}>
                  <Metric label="عن م50" value={m.dist_sma50 == null ? null : `${m.dist_sma50 >= 0 ? "+" : ""}${m.dist_sma50}%`}
                    color={m.dist_sma50 == null ? undefined : m.dist_sma50 >= 0 ? "var(--pos-ink)" : "var(--neg-ink)"} />
                  <Metric label="عن م200" value={m.dist_sma200 == null ? null : `${m.dist_sma200 >= 0 ? "+" : ""}${m.dist_sma200}%`}
                    color={m.dist_sma200 == null ? undefined : m.dist_sma200 >= 0 ? "var(--pos-ink)" : "var(--neg-ink)"} />
                  <Metric label="RSI" value={m.rsi == null ? null : String(m.rsi)}
                    color={m.rsi == null ? undefined : m.rsi < 30 ? "var(--pos-ink)" : m.rsi > 70 ? "var(--neg-ink)" : "var(--ink-muted)"} />
                </div>

                {/* صفّ التقييم — بنفس بنية الصفّ التقني أعلاه لا وسوماً
                    مبعثرة: ثلاثة أرقام في ثلاثة أعمدة، فتُقارَن الشركات
                    رأسياً بالنظر بين بطاقةٍ وأخرى.
                    والحكم شريطٌ تحتها لأنه خلاصةُ الثلاثة لا رابعُها. */}
                {/* صفّ الذكاء — ثلاث قوائم بلغة بطاقة «رؤية الذكاء» على الجوال:
                    التقييم يميناً · هدف المحللين رقماً في المنتصف · درجة
                    السلامة يساراً. والعناوين في سطرٍ واحد فوق، والقيم في سطرٍ
                    واحد تحت، فتُقارَن الشركات رأسياً بين بطاقةٍ وأخرى. */}
                {(r.upside_pct != null || r.fair_value != null || r.finance_score != null) && (
                  <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2.5" style={{ borderTop: "1px solid var(--line)" }}>
                    <div className="space-y-1.5 min-w-0">
                      <div className="text-[9.5px] text-[var(--ink-muted)]">التقييم</div>
                      {/* الشريط وحده هنا: كانت المعلومة نفسها تُقال ثلاث مرّات
                          (شريط + نصٌّ مقطوع «تقييم مبخ…» + وسمٌ أسفل البطاقة).
                          والنسبة رقمٌ يُقرأ، والوسم يبقى في صفّ الوسوم. */}
                      <div className="flex items-center gap-1.5 min-w-0">
                        <FairValueBar upside={r.upside_pct ?? null} hideLabel width={44} />
                        <span className="text-[10.5px] font-semibold tabular-nums shrink-0" dir="ltr"
                          style={{ color: fairValueTier(r.upside_pct ?? null).color }}>
                          {r.upside_pct == null ? "—" : `${r.upside_pct >= 0 ? "+" : ""}${Math.round(r.upside_pct)}%`}
                        </span>
                      </div>
                    </div>
                    {/* ══ رقمان لا يُخلطان ══ (D213)
                        حيث لا هدفَ لبيوت الخبرة — و‏124 شركةً كذلك، لأن أحداً
                        لا يُصدر لها توصية — تُعرض قيمةٌ نسبيةٌ إلى القطاع
                        مكانه. والعنوانُ نفسُه يتبدّل، فلا يُقرأ مضاعفُ قطاعٍ
                        على أنه رأيُ محلّل. ولونُها خافتٌ لأنها مشتقّةٌ لا
                        منقولة. */}
                    <div className="space-y-1.5 text-center">
                      <div className="text-[9.5px] text-[var(--ink-muted)]">
                        {r.fair_value == null && r.rel_value != null ? "نسبية للقطاع" : "هدف المحللين"}
                      </div>
                      <div className="text-[12px] font-bold tabular-nums" dir="ltr"
                        title={r.fair_value == null && r.rel_value != null
                          ? `قيمة نسبية إلى القطاع ${r.rel_low}–${r.rel_high} · ثقة ${r.rel_conf}`
                          : ""}
                        style={{ color: r.fair_value == null && r.rel_value != null ? "var(--ink-muted)" : "var(--ink)" }}>
                        {r.fair_value != null ? Number(r.fair_value).toFixed(2)
                          : r.rel_value != null ? Number(r.rel_value).toFixed(2) : "—"}
                      </div>
                    </div>
                    <div className="space-y-1.5 min-w-0">
                      <div className="text-[9.5px] text-[var(--ink-muted)] text-end">درجة السلامة</div>
                      <div className="flex items-center gap-1.5 justify-end">
                        <SafetyBar score={r.finance_score == null ? null : Math.round(r.finance_score)} width={44} />
                        <span className="text-[10.5px] font-semibold tabular-nums"
                          style={{ color: r.finance_score == null ? "var(--ink-muted)" : safeColor(r.finance_score) }}>
                          {r.finance_score == null ? "—" : Math.round(r.finance_score)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* الوسوم المتبقية — صفٌّ خاصّ بها */}
                {(r.verdict || r.sharia === "COMPLIANT" || r.dividend_yield != null || m.macd_cross) && (
                  <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
                    <VerdictTag v={r.verdict} small gap={r.value_gap_pct} basis={r.value_basis} />
                    {r.sharia === "COMPLIANT" && <Chip text="متوافق شرعاً" color="var(--pos-ink)" />}
                    {r.dividend_yield != null && <Chip text={`توزيع ${r.dividend_yield}%`} color="var(--info-ink)" />}
                    {m.macd_cross === "up" && <Chip text="ماكد صاعد" color="var(--pos-ink)" />}
                    {m.macd_cross === "down" && <Chip text="ماكد هابط" color="var(--neg-ink)" />}
                  </div>
                )}
              </button>
            );
          })}
          {shownMobile.length < shown.length && (
            <button onClick={() => setMobileCount(c => c + MOBILE_PAGE)}
              className="w-full py-2.5 text-[12px] font-semibold rounded-xl"
              style={{ border: "1px solid var(--hairline)", color: "var(--ink)" }}>
              عرض المزيد ({shown.length - shownMobile.length} متبقية)
            </button>
          )}
          {hidden > 0 && shownMobile.length >= shown.length && (
            <p className="text-[11px] text-center py-3" style={{ color: "var(--ink-muted)" }}>
              عُرضت أول {ROW_CAP} — {hidden.toLocaleString("en-US")} شركة أخرى مخفيّة. ضيّق الفلاتر لرؤيتها.
            </p>
          )}
        </div>

        {/* ══ الكمبيوتر: جدول ══ */}
        <div className="hidden md:block overflow-x-auto -mx-1">
          <table className="w-full text-[12px] tabular-nums">
            <thead>
              <tr className="text-start" style={{ borderBottom: "1px solid var(--hairline)" }}>
                <th className="px-2 py-2 text-[var(--ink-muted)] font-semibold text-start">الشركة</th>
                {th("price", "السعر")}
                {th("change_pct", "التغيّر")}
                {th("dist_sma50", "عن م50")}
                {th("dist_sma200", "عن م200")}
                {th("rsi", "RSI")}
                {th("dividend_yield", "التوزيعات")}
                {th("finance_score", "السلامة")}
                {th("value_gap_pct", "عن القطاع")}
                {th("upside_pct", "عن العادلة")}
                <th className="px-2 py-2 text-[var(--ink-muted)] font-semibold text-start whitespace-nowrap">الحكم</th>
                {th("high_52w", "قمة 52أ")}
                {th("low_52w", "قاع 52أ")}
              </tr>
            </thead>
            <tbody>
              {shown.map((r: any) => {
                const up = (r.change_pct ?? 0) >= 0;
                const m = M(r);   // مقاييس الفاصل المختار
                const rsiColor = m.rsi == null ? "var(--ink-muted)" : m.rsi < 30 ? "var(--pos-ink)" : m.rsi > 70 ? "var(--neg-ink)" : "var(--ink-muted)";
                const distColor = (v: any) => v == null ? "var(--ink-muted)" : v >= 0 ? "var(--pos-ink)" : "var(--neg-ink)";
                return (
                  <tr key={r.symbol} onClick={() => onOpen(r.symbol)}
                    className="cursor-pointer hover:bg-[var(--field)] transition-colors" style={{ borderBottom: "1px solid var(--hairline)" }}>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <CompanyLogo symbol={r.symbol} size={24} />
                        <div className="min-w-0">
                          <div className="text-[var(--ink)] text-[12px] font-semibold truncate max-w-[140px]">{r.name}</div>
                          <span className="tag-b" style={{ fontSize: 9 }}>{r.symbol}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-2 py-2 text-[var(--ink)] tabular-nums">{fmt(r.price)}</td>
                    <td className="px-2 py-2 font-bold" style={{ color: r.change_pct == null ? "var(--ink-muted)" : up ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                      {r.change_pct == null ? "—" : `${up ? "+" : ""}${r.change_pct.toFixed(2)}%`}
                    </td>
                    <td className="px-2 py-2 tabular-nums" style={{ color: distColor(m.dist_sma50) }}>{m.dist_sma50 == null ? "—" : `${m.dist_sma50 >= 0 ? "+" : ""}${m.dist_sma50}%`}</td>
                    <td className="px-2 py-2 tabular-nums" style={{ color: distColor(m.dist_sma200) }}>{m.dist_sma200 == null ? "—" : `${m.dist_sma200 >= 0 ? "+" : ""}${m.dist_sma200}%`}</td>
                    <td className="px-2 py-2 tabular-nums font-bold" style={{ color: rsiColor }}>{m.rsi == null ? "—" : m.rsi}</td>
                    <td className="px-2 py-2 tabular-nums" style={{ color: r.dividend_yield == null ? "var(--ink-muted)" : "var(--pos-ink)" }}>
                      {r.dividend_yield == null ? "—" : `${r.dividend_yield}%`}
                    </td>
                    <td className="px-2 py-2 tabular-nums text-[var(--ink)]">
                      {r.finance_score == null ? "—" : Math.round(r.finance_score)}
                      {r.sharia === "COMPLIANT" && <span className="text-[var(--pos-ink)] ms-1" title="متوافق شرعاً">✓</span>}
                    </td>
                    {/* الفجوة عن وسيط القطاع — موجبٌ يعني أرخص من أقرانه.
                        والأساس (مضاعف ربحية أم دفترية) يُعلَن في التلميح كي لا
                        يُقرأ رقمان مختلفا الأساس كأنهما واحد. */}
                    <td className="px-2 py-2 tabular-nums" dir="ltr"
                      title={r.value_basis === "pb" ? "الأساس: مكرّر القيمة الدفترية" : r.value_basis === "pe" ? "الأساس: مضاعف الربحية" : ""}
                      style={{ color: r.value_gap_pct == null ? "var(--ink-muted)" : r.value_gap_pct >= 20 ? "var(--pos-ink)" : r.value_gap_pct <= -20 ? "var(--neg-ink)" : "var(--ink-muted)" }}>
                      {r.value_gap_pct == null ? "—" : `${r.value_gap_pct > 0 ? "+" : ""}${Math.round(r.value_gap_pct)}%`}
                    </td>
                    {/* الفرق عن تقدير المحللين — مقياسٌ آخر لا امتداد للأول:
                        مصدره آراء بشر لا مقارنة أرقام، فيُعرض مستقلاً. */}
                    <td className="px-2 py-2 tabular-nums" dir="ltr"
                      title={r.fair_value ? `هدف المحللين ${r.fair_value}${r.fair_value_asof ? " · " + r.fair_value_asof : ""}`
                        : r.rel_value != null ? `قيمة نسبية إلى القطاع ${r.rel_value} (${r.rel_low}–${r.rel_high}) · ثقة ${r.rel_conf} — لا هدفَ محلّلين لهذه الشركة`
                        : ""}
                      style={{ color: r.upside_pct == null ? "var(--ink-muted)" : r.upside_pct >= 15 ? "var(--pos-ink)" : r.upside_pct <= -15 ? "var(--neg-ink)" : "var(--ink-muted)" }}>
                      {/* ولا يُدسّ المشتقُّ في خانة المنقول: علامةُ «≈» ولونٌ
                          خافتٌ يقولان إن هذا فرقٌ عن قيمةٍ نسبيةٍ لا عن هدفِ
                          محلّل (‏D213). */}
                      {r.upside_pct != null
                        ? `${r.upside_pct > 0 ? "+" : ""}${Math.round(r.upside_pct)}%`
                        : r.rel_value != null && r.price
                          ? <span className="text-[var(--ink-muted)]">{`≈${Math.round((r.rel_value - r.price) / r.price * 100) > 0 ? "+" : ""}${Math.round((r.rel_value - r.price) / r.price * 100)}%`}</span>
                          : "—"}
                    </td>
                    <td className="px-2 py-2"><VerdictTag v={r.verdict} gap={r.value_gap_pct} basis={r.value_basis} /></td>
                    <td className="px-2 py-2 text-[var(--ink-muted)] tabular-nums">{fmt(r.high_52w)}</td>
                    <td className="px-2 py-2 text-[var(--ink-muted)] tabular-nums">{fmt(r.low_52w)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* حصيلة الفرز — خارج كتلتي الجوال والكمبيوتر معاً. كان التنبيه داخل
            كتلة `hidden md:block`، فيراه مستخدم الكمبيوتر ولا يراه مستخدم
            الجوال مع أن القصّ يقع عليهما سواءً. والعدد يُعرض دائماً لا عند
            القصّ وحده: معرفة «كم شركة طابقت» جزءٌ من نتيجة الفرز نفسها. */}
        <div className="text-[11px] text-center py-3" style={{ borderTop: "1px solid var(--line)" }}>
          <span className="text-[var(--ink-muted)]">
            {filtered.length.toLocaleString("en-US")} شركة مطابقة
            {rows.length ? <span style={{ color: "var(--ink-muted)" }}> من {rows.length.toLocaleString("en-US")}</span> : null}
          </span>
          {hidden > 0 && (
            <span className="text-[var(--warn-ink)] block mt-1">
              عُرضت أول {ROW_CAP} — {hidden.toLocaleString("en-US")} شركة أخرى مخفيّة. ضيّق الفلاتر لرؤيتها.
            </span>
          )}
        </div>
        </>
      )}

      </>)}

      {/* ══ لوحة الفلاتر السفلية (جوال) ══
          مجمّعة بعناوين، بمساحة تنفّس، وأزرار إجراء واضحة أسفلها. */}
      {sheet && (
        <div className="md:hidden fixed inset-0 z-50 flex items-end" onClick={e => e.target === e.currentTarget && setSheet(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div className="relative w-full rounded-t-3xl p-4 pb-6 max-h-[85vh] overflow-y-auto fade-in"
            style={{ background: "var(--pop)", borderTop: "1px solid var(--line)" }}>
            <div className="w-10 h-1 rounded-full bg-[var(--ink-muted)] mx-auto mb-4" />
            <div className="flex items-center justify-between mb-4">
              <h3 className="card-title">فلاتر الفرز</h3>
              <button onClick={() => setSheet(false)} className="text-[var(--ink-muted)] p-1"><X size={18} /></button>
            </div>

            <div className="space-y-5">
              {/* الترتيب هنا لا في شريط الأدوات: كان صفّاً مستقلاً يزاحم
                  الفلاتر على شاشةٍ ضيّقة، وهو من جنسها — كلاهما يضبط ما
                  يُعرض. جمعُهما في لوحةٍ واحدة يُفرغ الشريط للأهمّ. */}
              <FilterGroup title="ترتيب النتائج">
                <div className="flex items-center gap-2">
                  <select value={sort.key} onChange={e => setSort(st => ({ key: e.target.value, dir: st.dir }))}
                    className="flex-1 rounded-xl px-3 py-2.5 text-[13px] text-[var(--ink)] focus:outline-none"
                    style={{ background: "var(--field)", border: "1px solid var(--field-line)" }}>
                    {SORT_OPTS.map(([k, lbl]) => <option key={k} value={k}>{lbl}</option>)}
                  </select>
                  <button onClick={() => setSort(st => ({ ...st, dir: st.dir === "desc" ? "asc" : "desc" }))}
                    className="flex items-center gap-1.5 px-3 text-[12px]"
                    style={{ background: "var(--field)", border: "1px solid transparent",
                             borderRadius: 12, height: 42,
                             color: sort.dir === "asc" ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                    {sort.dir === "asc" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                    {sort.dir === "asc" ? "تصاعدي" : "تنازلي"}
                  </button>
                </div>
              </FilterGroup>

              <FilterGroup title="القطاع">
                <select value={sector} onChange={e => setSector(e.target.value)}
                  className="w-full bg-[var(--field)] border border-[var(--hairline)] rounded-xl px-3 py-2.5 text-[13px] text-[var(--ink)] focus:outline-none">
                  <option value="">كل القطاعات</option>
                  {sectors.map(x => <option key={x} value={x}>{x}</option>)}
                </select>
              </FilterGroup>

              <FilterGroup title="المتوسطات المتحركة">
                <SheetRow label="السعر مقابل م50"><Seg value={ma50} set={setMa50} opts={[["above", "فوق"], ["below", "تحت"]]} /></SheetRow>
                <SheetRow label="السعر مقابل م200"><Seg value={ma200} set={setMa200} opts={[["above", "فوق"], ["below", "تحت"]]} /></SheetRow>
                <SheetRow label="الاتجاه"><Seg value={trend} set={setTrend} opts={[["golden", "صاعد"], ["death", "هابط"]]} /></SheetRow>
              </FilterGroup>

              <FilterGroup title="الزخم">
                <SheetRow label="RSI"><Seg value={rsiBand} set={setRsiBand} opts={[["oversold", "بيعي"], ["neutral", "محايد"], ["overbought", "شرائي"]]} /></SheetRow>
                <SheetRow label="ماكد"><Seg value={macd} set={setMacd} opts={[["up", "تقاطع صاعد"], ["down", "تقاطع هابط"]]} /></SheetRow>
                <SheetRow label="ماكد — الحالة"><Seg value={macd} set={setMacd} opts={[["bull", "فوق الإشارة"], ["bear", "تحت الإشارة"]]} /></SheetRow>
              </FilterGroup>

              <FilterGroup title="التقييم">
                <SheetRow label="أرخص من قطاعه ≥">
                  <input value={minGap} onChange={e => setMinGap(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-20 bg-[var(--field)] border border-[var(--hairline)] rounded-lg px-2 py-1.5 text-[13px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]" />
                </SheetRow>
                <SheetRow label="تحت هدف المحللين ≥">
                  <input value={minUpside} onChange={e => setMinUpside(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-20 bg-[var(--field)] border border-[var(--hairline)] rounded-lg px-2 py-1.5 text-[13px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]" />
                </SheetRow>
                <SheetRow label="الحكم">
                  <select value={verdict} onChange={e => setVerdict(e.target.value)}
                    className="bg-[var(--field)] border border-[var(--hairline)] rounded-lg px-2 py-1.5 text-[13px] text-[var(--ink)] focus:outline-none">
                    <option value="">الكل</option>
                    {VERDICT_FILTERS.map(k => <option key={k} value={k}>{VERDICTS[k].label}</option>)}
                  </select>
                </SheetRow>
              </FilterGroup>

              <FilterGroup title="الأساسي والشرعي">
                <SheetRow label="التوافق الشرعي"><Seg value={sharia} set={setSharia} opts={[["COMPLIANT", "متوافق"]]} /></SheetRow>
                <SheetRow label="التوزيعات ≥">
                  <input value={minYield} onChange={e => setMinYield(e.target.value)} inputMode="decimal" placeholder="٪"
                    className="w-20 bg-[var(--field)] border border-[var(--hairline)] rounded-lg px-2 py-1.5 text-[13px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]" />
                </SheetRow>
                <SheetRow label="درجة السلامة ≥">
                  <input value={minScore} onChange={e => setMinScore(e.target.value)} inputMode="decimal" placeholder="0-100"
                    className="w-20 bg-[var(--field)] border border-[var(--hairline)] rounded-lg px-2 py-1.5 text-[13px] text-[var(--ink)] text-center focus:outline-none placeholder:text-[var(--ink-muted)]" />
                </SheetRow>
              </FilterGroup>
            </div>

            <div className="flex gap-2 mt-6">
              <button onClick={reset} disabled={activeCount === 0}
                className="btn-ghost flex-1 justify-center disabled:opacity-40">مسح الكل</button>
              <button onClick={() => setSheet(false)} className="btn-primary flex-1 justify-center">
                عرض {filtered.length} نتيجة
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MarketPage() {
  const t = useT();
  const { tickers, language } = useAppStore();
  /* العودة من مصدر الخبر كانت تُعيد بناء صفحة السوق من الصفر: التبويب يعود
     إلى «الرئيسي» وموضع التمرير إلى الأعلى، فيضيع الخبر الذي كنتَ عنده.
     نحفظ التبويب وموضع التمرير في sessionStorage ونستعيدهما عند العودة —
     حفظٌ للجلسة وحدها، لا يمسّ بيانات ولا يبقى بعد إغلاق المتصفّح. */
  const [tab, setTab] = useState(() => {
    try { return sessionStorage.getItem("sp:market:tab") || "main"; } catch { return "main"; }
  });
  useEffect(() => {
    try { sessionStorage.setItem("sp:market:tab", tab); } catch { /* ممتلئ */ }
  }, [tab]);
  useEffect(() => {
    const KEY = "sp:market:scroll";
    /* التطبيق يُمرَّر داخل <main class="app-main"> لا في نافذة المتصفّح،
       فـwindow.scrollY صفرٌ دائماً — وأول محاولةٍ لحفظ الموضع كانت تحفظ
       صفراً وتستعيد صفراً. الحاوية هي المرجع الصحيح. */
    const el = document.querySelector(".app-main") as HTMLElement | null;
    if (!el) return;
    const save = () => {
      try { sessionStorage.setItem(KEY, String(el.scrollTop)); } catch { /* ممتلئ */ }
    };
    el.addEventListener("scroll", save, { passive: true });
    // pagehide يُطلق عند المغادرة إلى موقعٍ خارجي وعند تصغير التطبيق، وهو
    // الحدث الموثوق على iOS (unload لا يُطلق هناك).
    window.addEventListener("pagehide", save);
    const y = Number(sessionStorage.getItem(KEY) || 0);
    let tries = 0;
    // المحتوى يصل بعد الرسم الأول، فالاستعادة الفورية تقع على صفحةٍ قصيرة.
    // نحاول حتى يتّسع الارتفاع للموضع المحفوظ، بحدٍّ أقصى ثلاث ثوانٍ.
    const timer = y > 0 ? setInterval(() => {
      tries += 1;
      if (el.scrollHeight - el.clientHeight >= y) { el.scrollTop = y; clearInterval(timer); }
      else if (tries > 20) clearInterval(timer);
    }, 150) : null;
    return () => {
      if (timer) clearInterval(timer);
      el.removeEventListener("scroll", save);
      window.removeEventListener("pagehide", save);
    };
  }, []);
  const [stockSheet, setStockSheet] = useState<string | null>(null);
  /* المربّعُ يُفتح بأيقونة «نبض السوق» ويُغلق بعد قضاء الحاجة (D192).
     ويُفتح تلقائياً إن جاء رمزٌ من رابطٍ خارجيّ. */
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSymbol = searchParams.get("symbol");
  /* رمزٌ يأتي من رابطٍ خارجيّ يفتح ورقةَ السهم مباشرةً — كما لو بُحث عنه.
     ══ وموضعُه بعد التعريف لا قبله ══ (D211)
     كُتب فوقه فقرأ ثابتاً في «منطقة موته» (‏TDZ) — فرمى
     `ReferenceError` عند أوّل رسم فأطفأ تبويبَ السوق كلَّه. ولا يمسكه
     فحصُ الأنواع: الاسمُ **معرَّفٌ** في النطاق، والخطأُ في الترتيب. */
  useEffect(() => { if (initialSymbol) setStockSheet(initialSymbol.toUpperCase()); }, [initialSymbol]);
  const { data: overview } = useQuery({
    queryKey: ["market-overview"],
    queryFn: () => marketApi.overview().then(r => r.data.data),
    refetchInterval: 60000,
  });
  const { data: movers } = useQuery({
    queryKey: ["market-movers"],
    queryFn: () => marketApi.movers().then(r => r.data.data),
    refetchInterval: 30 * 60 * 1000,
  });
  const { data: news = [], isLoading } = useQuery({
    queryKey: ["market-news", language],
    queryFn: () => marketApi.news(language).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  const { data: events = [] } = useQuery({
    queryKey: ["market-events-wide"],
    queryFn: () => marketApi.eventsMarket().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  const { data: marketSummary } = useQuery({
    queryKey: ["market-summary"],
    queryFn: () => marketApi.summary().then(r => r.data.data),
    refetchInterval: 10 * 60 * 1000,
  });

  const enabled = [
    /* تاسي لم يعد بطاقةً مفردة: قيمته وتغيّره وحالته داخل «نبض السوق» —
       وعرضه مرّتين في شاشةٍ واحدة كان تكراراً لا تأكيداً. */
    tickers.brent && { key: "brent", variant: "ticker-brent", label: t("market.brent"), data: overview?.brent, prefix: "" },
  ].filter(Boolean) as any[];

  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)]">{t("market.title")}</h1>
      </div>

      {/* Tabs — أيقونة + اسم، تملأ العرض بالتساوي */}
      <div className="flex gap-2">
        {MARKET_TABS.map(mt => (
          <button key={mt.id} onClick={() => setTab(mt.id)} aria-pressed={tab === mt.id}
            /* بلا إطار — انظر تعليق تبويبات المحفظة في PortfolioPage. */
            className="flex-1 flex items-center justify-center gap-1.5 md:gap-2 px-2 md:px-3 py-2 md:py-2.5 rounded-xl text-[11px] md:text-sm transition-colors"
            style={tab === mt.id
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <mt.Icon size={16} className="shrink-0" />
            <span className="whitespace-nowrap">{mt.name}</span>
          </button>
        ))}
      </div>

      {tab === "main" && (
        <>
          {/* ══ لا بطاقةَ بحثٍ فوق النبض ══ (بأمر المالك · D210)
              البحثُ صار حقلاً يتمدّد داخل ترويسة «نبض السوق»، والنتيجةُ
              تُفتح في ورقة السهم نفسِها التي يفتحها الفرزُ والتوزيعُ
              وخريطةُ القطاعات — لا شاشةٌ رابعة. */}
          {/* While a stock result is on screen, the rest of the market widgets
              fade back and blur so focus stays on the result — they return the
              moment the search is closed. aria-hidden + pointer-events-none so
              the faded area isn't interactive or read out while hidden. */}
          {/* طبقةُ التلاشي أُلغيت مع صندوق البحث: الورقةُ تُفتح فوق الصفحة
              بطبقتها الخاصّة، فلا حاجةَ إلى إخفاء ما تحتها بضبابٍ ثانٍ. */}
          <div>
          <div className="space-y-5">

          {/* AI market summary — right under the lookup box, before the
              detailed numbers below. */}
          <PulseCard summary={marketSummary} tasi={overview?.tasi} brent={overview?.brent} movers={movers}
            onSearch={(sym: string) => setStockSheet(sym)} />

          {/* Ticker cards — user picks which ones in Settings */}
          {enabled.length > 0 && (
            <div className={`grid gap-4 ${enabled.length === 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"}`}>
              {enabled.map(tk => <TickerCard key={tk.key} variant={tk.variant} label={tk.label} data={tk.data} prefix={tk.prefix} />)}
            </div>
          )}

          {/* Market-only charts — TASI & Brent history side by side. */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <IndexHistoryCard symbol="^TASI.SR" title="منحنى مؤشر تاسي" icon="index" defaultRange="6mo" valueLabel="الإغلاق" />
            <IndexHistoryCard symbol="BZ=F" title="منحنى خام برنت" icon="brent" defaultRange="6mo" valueLabel="السعر" suffix="$" />
          </div>

          {/* Market mood + breadth. */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SentimentGaugeCard movers={movers} />
            <BreadthBarCard movers={movers} />
          </div>

          {/* Sector heatmap — full width. */}
          <SectorHeatmapCard movers={movers} />

          {/* Return distribution + sector leaders. */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ReturnDistributionCard movers={movers} />
            <SectorLeadersCard movers={movers} />
          </div>

          {/* Daily liquidity — full width. */}
          <LiquidityCard movers={movers} />

          {/* The specific names behind the breadth. */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MoversListCard title="الأعلى ارتفاعاً" rows={movers?.gainers} up />
            <MoversListCard title="الأعلى انخفاضاً" rows={movers?.losers} up={false} />
          </div>
          </div>
          </div>
        </>
      )}

      {/* الفرز يبقى **مركّباً ومخفياً** عند الانتقال لتبويبٍ آخر: تفكيكه كان
          يمحو الفلاتر والترتيب وموضع التمرير، فتعود إليه كأنك تدخله للتوّ.
          وبطاقة الشركة تُفتح **فوقه** لا في تبويب آخر — الضغط على شركة كان
          يبدّل التبويب فيفقد كل ذلك مرّةً واحدة. */}
      <div style={{ display: tab === "screener" ? undefined : "none" }}>
        <ScreenerTab onOpen={(symbol) => setStockSheet(symbol)} />
      </div>
      {stockSheet && <StockSheet symbol={stockSheet} onClose={() => setStockSheet(null)} />}

      {tab === "news" && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Newspaper size={16} className="text-[var(--warn-ink)]" />
            <h2 className="card-title">{t("market.news")}</h2>
            {news.some((n: any) => n.source === "AI") && <span className="tag-v ms-auto">{t("market.aiGenerated")}</span>}
          </div>
          <NewsList news={news} isLoading={isLoading} emptyText={t("market.noNews")} pageSize={60} />
        </div>
      )}

      {tab === "calendar" && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <CalendarDays size={16} className="text-[var(--brand-ink)]" />
            <h2 className="card-title">{t("market.calendar")}</h2>
          </div>
          {/* اللغة الموحدة للمفكرة: إعلانات الشركات فقط (معزولة عن الأخبار)،
              كل إعلان بشعار شركته وتصنيفه، مرتّبة أسبوعياً. */}
          <EventsList events={events} />
        </div>
      )}
    </div>
  );
}
