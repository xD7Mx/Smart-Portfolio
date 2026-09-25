import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Plus, Search, Pencil, Trash2, TrendingUp, TrendingDown, ShoppingCart, X, SlidersHorizontal, Wallet, Scale, Columns3, RefreshCw, Coins, LayoutGrid, Briefcase, Newspaper, CalendarDays, GripVertical, Star, ChevronDown, AlertTriangle, Droplets, Save } from "lucide-react";
import { GridLayout, useContainerWidth, verticalCompactor } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import { companiesApi, holdingsApi, transactionsApi, cashApi, allocationApi, portfolioApi, profileApi } from "../services/api";
import { useT } from "../i18n";
import { searchCompanies, lookupCompany, SaudiCompany } from "../data/saudiCompanies";
import StockSheet from "../components/market/StockSheet";
import { weightedDividendYield, retainedCashPct, rescaleWeights, rebalanceRow } from "../lib/allocMath";
import AllocationCharts from "../components/portfolio/AllocationCharts";
import { useAppStore, GridItem } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import CompanyLogo from "../components/common/CompanyLogo";
import { ShariaBadge, NumInput } from "../components/common/UI";
import { WealthW, WIDGET_MAP } from "../widgets/Widgets";
import FlashPrice from "../components/common/FlashPrice";
import LivePrice, { LiveValue } from "../components/common/LivePrice";
import LiquidityTab from "../components/portfolio/LiquidityTab";
import PortfolioNewsPage from "./PortfolioNewsPage";
import PortfolioCalendarPage from "./PortfolioCalendarPage";
import NotificationsPage from "./NotificationsPage";
import PortfolioSwitcher from "../components/portfolio/PortfolioSwitcher";
import { AvatarImg } from "../components/common/Avatar";
import WatchlistTab from "../components/market/WatchlistTab";
import CollapsibleList from "../components/common/CollapsibleList";

const MOBILE_BREAKPOINT = 680;
const TABLET_BREAKPOINT = 1024;
const TABLET_COLS = 6;

// ── لوحة التحكم (شبكة الودجزات) — منقولة من صفحة Dashboard السابقة إلى
// تبويب داخل المحفظة، لتجميع كل ما يخص المحفظة في مكان واحد ─────────────
// ودجزات تُخفى على الجوال فقط: المركز الثالث في الأعلى ارتفاعاً/انخفاضاً —
// اثنان يكفيان على شاشة ضيقة (الكمبيوتر يبقى ثلاثة). تصفية عرضٍ بحتة: الحفظ
// معطّل أصلاً على الجوال، فلا يتأثّر التخطيط المحفوظ للكمبيوتر.
const MOBILE_HIDDEN_WIDGETS = new Set(["gainer3", "loser3"]);

function mobileReflow(grid: GridItem[]): GridItem[] {
  const items = [...grid]
    .filter(it => !MOBILE_HIDDEN_WIDGETS.has(it.i))
    .sort((a, b) => (a.y - b.y) || (a.x - b.x));
  const out: GridItem[] = [];
  let y = 0;
  let halfOpen = false;
  for (const it of items) {
    const isSmall = it.h <= 1;
    if (isSmall) {
      if (!halfOpen) { out.push({ ...it, x: 0, y, w: 1, h: 1 }); halfOpen = true; }
      else { out.push({ ...it, x: 1, y, w: 1, h: 1 }); halfOpen = false; y += 1; }
    } else {
      if (halfOpen) { y += 1; halfOpen = false; }
      out.push({ ...it, x: 0, y, w: 2, h: it.h });
      y += it.h;
    }
  }
  return out;
}

function tabletReflow(grid: GridItem[]): GridItem[] {
  return grid.map(it => ({
    ...it,
    x: Math.round(it.x / 2),
    w: Math.max(1, Math.min(TABLET_COLS, Math.round(it.w / 2))),
  }));
}

function mirrorRtl(grid: GridItem[], cols: number): GridItem[] {
  return grid.map(it => ({ ...it, x: cols - it.x - it.w }));
}

// ترحيب شخصي كأنظمة التشغيل: تحية حسب الوقت + اسم المستخدم + صورته إن وُجدت.
function Greeting({ fallback }: { fallback: string }) {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: () => profileApi.get().then(r => r.data.data) });
  const name = (profile?.name || "").trim();
  const h = new Date().getHours();
  const greet = h < 5 ? "ليلة هانئة" : h < 12 ? "صباح الخير" : h < 17 ? "طاب يومك" : h < 22 ? "مساء الخير" : "مساء الخير";
  return (
    <div className="flex items-center gap-3">
      {profile?.has_avatar && (
        <div className="w-11 h-11 rounded-full overflow-hidden border border-[var(--hairline)] shrink-0 flex items-center justify-center panel">
          <AvatarImg iconSize={20} />
        </div>
      )}
      <div className="min-w-0">
        <h1 className="text-2xl font-medium text-[var(--ink)] truncate">{name ? `${greet}، ${name}` : fallback}</h1>

      </div>
    </div>
  );
}

function DashboardGrid() {
  const { activeLayout, layouts, setActiveLayout, saveGrid } = useAppStore();
  const { isOwner } = useAuthStore();
  const { width, containerRef, mounted } = useContainerWidth();

  const layout = layouts[activeLayout] ?? Object.values(layouts)[0];
  // Drop any layout item whose widget no longer exists (e.g. تاسي/برنت after
  // removal). Even if a persisted layout still lists them, they'd otherwise
  // render as hidden divs that STILL reserve their grid cells — leaving the
  // empty gap the user sees. Filtering here removes the reserved space
  // regardless of whether the store migration ran.
  const grid = (layout?.grid ?? []).filter((it: any) => WIDGET_MAP[it.i]);

  const isMobile = mounted && width > 0 && width < MOBILE_BREAKPOINT;
  const isTablet = mounted && width >= MOBILE_BREAKPOINT && width < TABLET_BREAKPOINT;
  const reflowedGrid = isMobile ? mobileReflow(grid) : isTablet ? tabletReflow(grid) : grid;
  const cols = isMobile ? 2 : isTablet ? TABLET_COLS : 12;
  // Drag/resize are disabled, so GridLayout never compacts the initial layout
  // on its own — any vertical gap left by a removed widget would persist.
  // Compact here so rows always pull up to fill the gap.
  const compactedGrid = verticalCompactor.compact(reflowedGrid as any, cols) as typeof reflowedGrid;
  const renderGrid = mirrorRtl(compactedGrid, cols);

  return (
    <>
      {Object.keys(layouts).length > 1 && (
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <LayoutGrid size={14} className="text-[var(--ink-muted)]" />
          {/* مبدّلٌ واحدٌ في التطبيق — لغةُ `.seg` نفسُها (D202). */}
          <div className="seg inline-flex w-fit">
            {Object.entries(layouts).map(([id, l]) => (
              <button key={id} onClick={() => setActiveLayout(id)} aria-pressed={activeLayout === id}
                className={"seg-btn whitespace-nowrap" + (activeLayout === id ? " on" : "")}>
                {l.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <div ref={containerRef} dir="ltr">
        {mounted && grid.length > 0 && (
          <GridLayout
            width={width}
            layout={renderGrid as any}
            gridConfig={isMobile
              ? { cols: 2, rowHeight: 120, margin: [10, 10], containerPadding: [0, 0] }
              : isTablet
              ? { cols: TABLET_COLS, rowHeight: 120, margin: [10, 10], containerPadding: [0, 0] }
              : { cols: 12, rowHeight: 120, margin: [12, 12], containerPadding: [0, 0] }}
            // السحب لإعادة الترتيب: للمالك وعلى الكمبيوتر فقط (لا نحفظ ترتيب
            // إعادة التدفّق على الجوال/التابلت فوق ترتيب الكمبيوتر). المقبض
            // grip فقط يبدأ السحب كي لا يتعارض مع أزرار الودجات.
            dragConfig={{ enabled: isOwner && !isMobile && !isTablet, handle: ".drag-handle" }}
            // تغيير الحجم: للمالك على الكمبيوتر — كان معطّلاً كلياً فتعذّر
            // تصغير أي بطاقة (مثل «توزيع القطاعات») لتصير نصف صفّ.
            resizeConfig={{ enabled: isOwner && !isMobile && !isTablet }}
            compactor={verticalCompactor}
            onDragStop={(newLayout: any) => {
              if (isMobile || isTablet) return;
              const byId = new Map(grid.map(g => [g.i, g]));
              // نُعيد الإحداثيات من الوضع المعكوس (RTL) إلى المنطقي ثم نحفظ.
              const logical = mirrorRtl(newLayout as any, cols)
                .map((it: any) => ({ ...(byId.get(it.i) || {}), i: it.i, x: it.x, y: it.y, w: it.w, h: it.h }));
              saveGrid(logical as any);
            }}
            onResizeStop={(newLayout: any) => {
              if (isMobile || isTablet) return;
              const byId = new Map(grid.map(g => [g.i, g]));
              const logical = mirrorRtl(newLayout as any, cols)
                .map((it: any) => ({ ...(byId.get(it.i) || {}), i: it.i, x: it.x, y: it.y, w: it.w, h: it.h }));
              saveGrid(logical as any);
            }}
          >
            {renderGrid.map(item => {
              const def = WIDGET_MAP[item.i];
              if (!def) return <div key={item.i} style={{display:"none"}} />;
              const C = def.component;
              return (
                <div key={item.i} className="mc relative group" style={{overflow: "auto", display: "flex", flexDirection: "column"}} dir="rtl">
                  {isOwner && !isMobile && !isTablet && (
                    <span className="drag-handle absolute top-1 end-1 z-20 p-0.5 rounded text-[var(--hairline)] hover:text-[var(--brand-ink)] cursor-move opacity-0 group-hover:opacity-100 transition-opacity"
                      title="اسحب لإعادة ترتيب الشاشات"><GripVertical size={13} /></span>
                  )}
                  <div className="flex-1 min-h-0"><C /></div>
                </div>
              );
            })}
          </GridLayout>
        )}
      </div>
    </>
  );
}

const fmt = (n: number) => n?.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) ?? "—";
const fmt2 = (n: number) => n?.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "0.00";

/* لوحةُ تمييزٍ بين الشركات — عشرُ درجاتٍ متباينة، لا دلالةَ ربحٍ وخسارة.
   لا تُستبدل برموز `--pos-ink/--neg-ink`: تلك للمعنى لا للتفريق، وقد
   أفسدت شريطَي «سابك» و«جرير» حين دخلت داخل `color-mix` في التدرّج
   فبطل التدرّج ولم يُرسم الشريطان أصلاً. */
/* اللوحة الأساسية الأولى (ما قبل 3d96cf1) بترتيبها الأصلي، لكنْ بالرموز
   لا بقيمٍ ثابتة: القيمة الثابتة لا تعرف المظهر ولا يطالها تغييرٌ لاحق.
   وأُخرجت منها أحبار الدلالة التي كانت مدسوسةً في مواضع ٣ و٦: الأخضر
   والأحمر هنا يقولان «القطاع رقم ٣» وهو معنًى لا يملكانه — والقاعدة
   نفسها هي ما جعل الأشرطة تُقرأ صارخةً. */
const COMPO_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--chart-8)", "var(--chart-9)", "var(--chart-10)"];

// ── Portfolio composition — colorful proportional strip of holdings by weight ──
function CompositionCard({ holdings }: { holdings: any[] }) {
  const total = holdings.reduce((a, h) => a + (h.current_value || 0), 0);
  const items = holdings
    .map((h: any) => ({
      name: lookupCompany(h.company?.symbol)?.name_ar || h.company?.name_ar || h.company?.name || h.company?.symbol,
      symbol: h.company?.symbol,
      value: h.current_value || 0,
      pct: total ? (h.current_value || 0) / total * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value)
    .map((it, i) => ({ ...it, color: COMPO_COLORS[i % COMPO_COLORS.length] }));

  return (
    <div className="card">
      <p className="card-title mb-4">تكوين المحفظة</p>
      {/* Colorful proportional bar */}
      <div className="flex w-full rounded-full overflow-hidden" style={{ height: 34 }}>
        {items.map((it) => (
          <div key={it.symbol} title={`${it.name} — ${it.pct.toFixed(1)}%`}
            style={{ width: `${it.pct}%`, background: `linear-gradient(180deg, ${it.color}, ${it.color}cc)` }}
            className="h-full transition-all hover:brightness-110" />
        ))}
      </div>
      {/* دليل الشركات — ظاهر مباشرةً بلا قائمة منسدلة */}
      <div className="grid grid-cols-2 gap-x-5 gap-y-2 mt-4">
        {items.map((it) => (
          <div key={it.symbol} className="flex items-center gap-2 text-[12.5px] min-w-0">
            <span className="rounded-full shrink-0" style={{ width: 9, height: 9, background: it.color }} />
            <span className="text-[var(--ink)] truncate flex-1">{it.name}</span>
            <span className="font-bold text-[var(--ink)] shrink-0">{it.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Portfolio charts: composition + company performance metric ────
function PerformanceColumnChart({ data, mode }: { data: { name: string; symbol: string; profit: number; capitalGain: number; dividends: number; divYield: number }[]; mode: "profit" | "yield" }) {
  const [hover, setHover] = useState<number | null>(null);
  const values = data.map(d => mode === "profit" ? d.profit : d.divYield);
  const posMax = Math.max(0, ...values, 1e-9);
  const negMax = Math.max(0, ...values.map(v => -v), 1e-9);
  const hasNeg = negMax > 1e-9;
  const total = posMax + negMax;
  const topPct = hasNeg ? Math.max((posMax / total) * 100, 15) : 100;
  const bottomPct = 100 - topPct;

  return (
    <div className="relative" style={{ height: 190 }} dir="ltr">
      <div className="flex h-full items-stretch gap-3">
        {data.map((d, i) => {
          const v = mode === "profit" ? d.profit : d.divYield;
          const positive = v >= 0;
          const color = positive ? "var(--pos-ink)" : "var(--neg-ink)";
          const barHeightPct = positive
            ? (posMax > 0 ? (v / posMax) * topPct : 0)
            : (negMax > 0 ? (-v / negMax) * bottomPct : 0);
          return (
            <div key={d.name} className="flex-1 min-w-0 flex flex-col h-full"
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              /* على الجوّال لا وجودَ لتحويم: اللمس يكشف الاسم والرقم. */
              onClick={() => setHover(h => h === i ? null : i)}>
              <div style={{ height: `${topPct}%` }} className="flex flex-col justify-end">
                {positive && (
                  <div className="relative w-full rounded-t-lg overflow-hidden transition-transform duration-150"
                    style={{
                      height: `${barHeightPct}%`, minHeight: v !== 0 ? 4 : 0,
                      background: `linear-gradient(180deg, color-mix(in srgb, ${color} 100%, white 25%) 0%, ${color} 60%, color-mix(in srgb, ${color} 100%, black 20%) 100%)`,
                      transform: hover === i ? "translateY(-2px)" : undefined,
                    }}>
                    <div className="absolute top-0 inset-x-0 h-2/5" style={{ background: "transparent, transparent)" }} />
                  </div>
                )}
              </div>
              {hasNeg && <div className="w-full shrink-0" style={{ height: 1, background: "var(--line)" }} />}
              {hasNeg && (
                <div style={{ height: `${bottomPct}%` }} className="flex flex-col justify-start">
                  {!positive && (
                    <div className="relative w-full rounded-b-lg overflow-hidden transition-transform duration-150"
                      style={{
                        height: `${barHeightPct}%`, minHeight: v !== 0 ? 4 : 0,
                        background: `linear-gradient(0deg, color-mix(in srgb, ${color} 100%, white 25%) 0%, ${color} 60%, color-mix(in srgb, ${color} 100%, black 20%) 100%)`,
                        transform: hover === i ? "translateY(2px)" : undefined,
                      }}>
                      <div className="absolute bottom-0 inset-x-0 h-2/5" style={{ background: "transparent, transparent)" }} />
                    </div>
                  )}
                </div>
              )}
              {/* الشعار بدل الاسم: ثماني أعمدة على عرض الجوّال تترك لكل اسمٍ
                  نحو أربعين بكسل، فكان «الاتصالات السعودية» يخرج «الاتص…»
                  ولا يُعرَف منه شيء. الشعار يُعرف من لمحة، والاسم الكامل
                  يبقى في التلميح عند اللمس أو التحويم — ولمن لا شعار له
                  يعود الرمز نصّاً، فلا يبقى العمود مجهولاً أبداً. */}
              <div className="mt-1.5 flex justify-center" title={d.name} aria-label={d.name}>
                <CompanyLogo symbol={d.symbol} size={22} />
              </div>
            </div>
          );
        })}
      </div>
      {hover !== null && (
        <div className="absolute z-10 rounded-xl px-3 py-2 text-xs pointer-events-none whitespace-nowrap top-1 start-1"
          style={{ background: "var(--pop)", border: "1px solid var(--line)" }}>
          <p className="font-bold mb-0.5" style={{ color: "var(--tip-text)" }}>{data[hover].name}</p>
          {mode === "profit" ? (
            <p style={{ color: "var(--tip-text)" }} className="opacity-80">{fmt(data[hover].profit)} (رأسمالي {fmt(data[hover].capitalGain)} + توزيعات {fmt(data[hover].dividends)})</p>
          ) : (
            <p style={{ color: "var(--tip-text)" }} className="opacity-80">{data[hover].divYield.toFixed(2)}% ({fmt(data[hover].dividends)} من إجمالي التكلفة)</p>
          )}
        </div>
      )}
    </div>
  );
}

function PortfolioCharts({ holdings }: { holdings: any[] }) {
  const [mode, setMode] = useState<"profit" | "yield">("profit");
  const withValue = holdings.filter((h: any) => (h.current_value || 0) > 0);
  if (withValue.length === 0) return null;

  const rows = withValue.map((h: any) => {
    const capitalGain = (h.current_value || 0) - (h.total_cost || 0);
    const dividends = h.total_dividends_received || 0;
    const divYield = h.total_cost ? (dividends / h.total_cost) * 100 : 0;
    return {
      name: lookupCompany(h.company?.symbol)?.name_ar || h.company?.name_ar || h.company?.name || h.company?.symbol,
      symbol: h.company?.symbol || "",
      profit: capitalGain + dividends,
      capitalGain,
      dividends,
      divYield,
    };
  });
  // Ascending so the highest value ends up last — the column chart lays out
  // in dir="ltr" order, so this puts the biggest bar rightmost.
  const chartData = [...rows]
    .sort((a, b) => (mode === "profit" ? a.profit - b.profit : a.divYield - b.divYield))
    .slice(-8);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <CompositionCard holdings={withValue} />
      <div className="card">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <p className="card-title">مقياس أداء الشركات</p>
          <div className="flex gap-1">
            <button onClick={() => setMode("profit")}
              className={"px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all " +
                (mode === "profit" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              الأرباح
            </button>
            <button onClick={() => setMode("yield")}
              className={"px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all " +
                (mode === "yield" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              التوزيعات
            </button>
          </div>
        </div>
        <PerformanceColumnChart data={chartData} mode={mode} />
      </div>
    </div>
  );
}

// ── Modal components ─────────────────────────────────────────
function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={`modal-box fade-in${wide ? " modal-wide" : ""}`}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="modal-title">{title}</h2>
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="label">{label}</label>{children}</div>;
}

// ── Add/Edit Company Modal ────────────────────────────────────
function CompanyModal({ company, onClose }: { company?: any; onClose: () => void }) {
  const t = useT();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    symbol:   company?.symbol   ?? "",
    name:     company?.name     ?? "",
    name_ar:  company?.name_ar  ?? "",
    sector:   company?.sector   ?? "",
    market:   company?.market   ?? "تداول",
    currency: company?.currency ?? "SAR",
  });
  const [suggestions, setSuggestions] = useState<SaudiCompany[]>([]);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  // Live Saudi market directory from Sahmak (real symbols + Arabic/English
  // names); merged with the built-in list, so search works even before a key.
  const { data: directory = [] } = useQuery({
    queryKey: ["market-directory"],
    queryFn: () => companiesApi.directory().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 0,
  });

  // Autocomplete: search by symbol / Arabic name / English name, then autofill everything
  const onSymbolInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setForm(f => ({ ...f, symbol: v }));
    const q = v.trim().toLowerCase();
    const local = searchCompanies(v);
    const seen = new Set(local.map(c => c.symbol));
    const remote: SaudiCompany[] = q
      ? directory
          .filter((c: any) => {
            const sym = String(c.symbol || "");
            return !seen.has(sym) && (sym.startsWith(q) || (c.name || "").includes(v) || (c.name_en || "").toLowerCase().includes(q));
          })
          .slice(0, 8)
          .map((c: any) => ({ symbol: String(c.symbol), name_ar: c.name || c.name_en, name_en: c.name_en || c.name, sector: "" }))
      : [];
    setSuggestions([...local, ...remote].slice(0, 10));
  };
  const pick = (c: SaudiCompany) => {
    setForm(f => ({ ...f, symbol: c.symbol, name: c.name_en, name_ar: c.name_ar, sector: c.sector }));
    setSuggestions([]);
  };

  const mutation = useMutation({
    mutationFn: () => company
      ? companiesApi.update(company.id, form).then(r => r.data)
      : companiesApi.add(form).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); onClose(); },
  });

  return (
    <Modal title={company ? t("port.editCompany") : t("port.newCompany")} onClose={onClose}>
      <div className="space-y-3">
        <Field label="ابحث بالرمز أو الاسم (عربي/إنجليزي)">
          <div className="relative">
            <input className="input" value={form.symbol} onChange={onSymbolInput}
              placeholder="2222 · أرامكو · Aramco" autoFocus />
            {/* القائمة تندمج بأرضية التطبيق ويحدّها إطارٌ أثقل — كصندوق
                البحث فوقها تماماً. الصنف `sp-menu` يحمل اللون فلا يتكرّر
                القرار في كل موضعِ قائمة. */}
            {suggestions.length > 0 && (
              <div className="sp-menu absolute z-20 top-full mt-1 w-full rounded-xl overflow-hidden shadow-2xl"
                style={{maxHeight: 220, overflowY: "auto"}}>
                {suggestions.map(c => (
                  <button key={c.symbol} type="button"
                    className="w-full text-start px-3 py-2.5 hover:bg-[var(--field)] flex items-center gap-3 transition-colors"
                    onClick={() => pick(c)}>
                    <CompanyLogo symbol={c.symbol} size={26} />
                    <span className="tag-b shrink-0">{c.symbol}</span>
                    <span className="text-[var(--ink)] text-sm font-semibold">{c.name_ar}</span>
                    <span className="text-[var(--ink-muted)] text-xs ms-auto">{c.name_en} · {c.sector}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("common.sector")}><input className="input" value={form.sector} onChange={set("sector")} placeholder="—" /></Field>
          <div />
        </div>
        <Field label={t("port.nameEn")}><input className="input" value={form.name} onChange={set("name")} placeholder="Aramco" /></Field>
        <Field label={t("port.nameAr")}><input className="input" value={form.name_ar} onChange={set("name_ar")} placeholder="أرامكو السعودية" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("port.marketField")}>
            <select className="input" value={form.market} onChange={set("market")}>
              <option>تداول</option><option>نوماد</option><option>السوق الموازية</option>
            </select>
          </Field>
          <Field label={t("port.currency")}>
            <select className="input" value={form.currency} onChange={set("currency")}>
              <option>SAR</option><option>USD</option>
            </select>
          </Field>
        </div>
        <div className="flex gap-3 pt-2">
          <button className="btn-primary flex-1" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </button>
          <button className="btn-ghost" onClick={onClose}>{t("common.cancel")}</button>
        </div>
        {mutation.isError && <p className="text-[var(--neg-ink)] text-xs">{t("common.error")}</p>}
      </div>
    </Modal>
  );
}

// ── Transaction Modal — full investment-reference engine ─────
// 4 simple rules, no exceptions: توزيع نقدي وبيع يزيدان السيولة دائمًا،
// شراء ينقصها دائمًا (بوسم اختياري توزيع/تصفية للتقارير فقط، لا يغيّر شيئًا
// حسابيًا)، ومنحة الأسهم تزيد الكمية بدون أي أثر على التكلفة أو السيولة.
/* الشفافية بـ`color-mix` لا بلصق لاحقةٍ ستّ عشرية: `var(--pos-ink)22`
   قيمةٌ غير صالحة، فكان زرّا «شراء» و«بيع» وحدهما بلا لونٍ ولا إطار عند
   اختيارهما — لأنهما الوحيدان اللذان يأخذان لونهما من رمز. */
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;

const TX_TYPES = [
  { id: "BUY",      label: "شراء",       color: "var(--pos-ink)" },
  { id: "SELL",     label: "بيع",        color: "var(--neg-ink)" },
  { id: "DIVIDEND", label: "توزيع نقدي", color: "var(--warn-ink)" },
  { id: "BONUS",    label: "منحة أسهم",  color: "var(--chart-3)" },
  { id: "SPLIT",    label: "تجزئة",      color: "var(--chart-7)" },
];
const FUNDING_SOURCES = [
  // خياران لا ثلاثة: مالٌ جديد من خارج المحفظة، أو مالٌ عاد منها (توزيعات أو
  // حصيلة تصفية معاً — النقد لا لون له فالتفريق بينهما تصنيفٌ لا واقعة).
  { id: "",         label: "ضخ",              color: "var(--ink-muted)" },
  { id: "REINVEST", label: "إعادة استثمار",   color: "var(--chart-6)" },
];

function TransactionModal({ company, onClose }: { company: any; onClose: () => void }) {
  const tr = useT();
  const qc = useQueryClient();
  const [type, setType] = useState("BUY");
  const [fundingSource, setFundingSource] = useState("");
  const [f, setF] = useState({ shares: "", price: "", amount: "", factor: "2", date: new Date().toISOString().split("T")[0] });
  const [preSplitOk, setPreSplitOk] = useState(false);
  // سياق القرار داخل البطاقة: أسهمك · متوسط تكلفتك · سيولتك.
  const { data: holdingCtx } = useQuery({
    queryKey: ["holding", company.id],
    queryFn: () => holdingsApi.get(company.id).then(r => r.data.data).catch(() => null),
  });
  // نصيب هذا السهم من إعادة التوازن — بصنفيه: سيولة وإعادة استثمار، بنفس
  // الحساب المعروض في بطاقة «التوزيع النسبي» (وزنه المستهدف من كلّ مصدر).
  const { data: allocCtx } = useQuery({
    queryKey: ["allocation"],
    queryFn: () => allocationApi.get().then(r => r.data.data).catch(() => null),
    // حسابٌ على كل الحيازات — لا داعي له وأنت تسجّل توزيعاً أو منحة.
    enabled: type === "BUY" || type === "SELL",
  });
  const { data: cashCtx } = useQuery({
    queryKey: ["cash"], queryFn: () => cashApi.get().then(r => r.data?.data),
    enabled: type === "BUY",
  });
  const myAlloc = (allocCtx?.items ?? []).find((x: any) => x.company_id === company.id);
  const upd = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setF(s => ({ ...s, [k]: e.target.value }));
  /* نظيرٌ للحقول الرقمية: NumInput يمرّر القيمة نصّاً لا حدثاً. */
  const updV = (k: string) => (v: string) => setF(s => ({ ...s, [k]: v }));

  /* تبديل النوع يُصفّر الحقول الرقمية: قيمةٌ محمولة من نوعٍ سابق (١٠٠ سهم
     كُتبت لشراء ثم صار النوع «منحة») تُسجَّل بلا انتباه وتعدّل حيازتك. التاريخ
     يبقى لأنه لا يتغيّر بتغيّر النوع. */
  const changeType = (id: string) => {
    setType(id);
    setF(s => ({ ...s, shares: "", price: "", amount: "", factor: "2" }));
    if (id !== "BUY") setFundingSource("");
  };

  const mutation = useMutation({
    mutationFn: () => {
      const payload: any = { company_id: company.id, transaction_type: type, transaction_date: f.date };
      if (type === "BUY" || type === "SELL") { payload.shares = Number(f.shares); payload.price_per_share = Number(f.price); }
      if (type === "BUY" && fundingSource) { payload.funding_source = fundingSource; }
      if (type === "DIVIDEND") { payload.amount = Number(f.amount); }
      if (type === "BONUS") {
        payload.shares = Number(f.shares);
        // سعر يوم المنح — يُثبّت قيمة المنحة في «العائد المحقّق» فلا تتحرّك
        // مع السوق كل يوم. اختياري: بلا سعرٍ يُقدَّر بالسعر الأخير.
        if (Number(f.price) > 0) payload.price_per_share = Number(f.price);
      }
      if (type === "SPLIT") { payload.factor = Number(f.factor); payload.confirm_prior_pre_split = preSplitOk; }
      return transactionsApi.add(payload).then(r => r.data);
    },
    onSuccess: () => {
      /* **إبطالٌ شامل بعد كل عملية** — لا قائمةٌ موجَّهة.
         العلّة التي يعالجها: القائمة الموجَّهة كانت تُبطل «portfolio» ظنّاً
         أنها تشمل «portfolio-metrics»، ومطابقة المفاتيح في react-query
         تُقارن العناصر لا البادئات النصّية — فـ["portfolio"] لا تُطابق
         ["portfolio-metrics"]. النتيجة: تسجّل توزيعاً فيتحدّث النقد والحيازة،
         ويبقى **صافي الربح وعائد المحفظة والأهداف والدخل** على أرقامٍ قديمة.
         ومع تمديد صلاحية الكاش إلى خمس دقائق صار العُطل أطول عمراً.
         القائمة تُنسى مع كل بطاقةٍ جديدة تُضاف؛ والقاعدة لا تُنسى: أي كتابة
         على بيانات المحفظة تُبطل كل ما هو مقروء. الكلفة استجلابٌ واحد بعد
         فعلٍ يقوم به المالك عمداً — والمقابل ألّا يرى رقماً قديماً أبداً. */
      qc.invalidateQueries();
      onClose();
    },
  });

  // ما سيحدث فعلاً بالأرقام — يُحسب من مدخلاتك ومن حيازتك الحالية.
  const shares0 = Number(holdingCtx?.total_shares ?? 0);
  const invested0 = Number(holdingCtx?.invested_amount ?? 0);
  const addQty = Number(f.shares) || 0;
  const addAmt = addQty * (Number(f.price) || 0);
  const newAvgCost = (shares0 + addQty) > 0 ? (invested0 + addAmt) / (shares0 + addQty) : 0;

  const baseValid =
    (type === "BUY" || type === "SELL") ? Number(f.shares) > 0 && Number(f.price) > 0 :
    type === "DIVIDEND" ? Number(f.amount) > 0 :
    type === "BONUS" ? Number(f.shares) > 0 :
    Number(f.factor) > 0;

  /* نفس حراسات الخادم، مطبَّقة هنا أيضاً: الخادم يرفض بيعاً فوق الحيازة أو
     شراءً فوق السيولة، لكن ترك الزرّ مُفعَّلاً يعني ضغطاً وانتظاراً ثم رفضاً.
     المنع قبل الإرسال أسرع وأوضح. الخادم يبقى الحكم — هذه راحةٌ لا بديل. */
  const availCash = Number(cashCtx?.available_cash ?? 0);
  const blockReason: string | null =
    type === "SELL" && Number(f.shares) > shares0
      ? `لا تملك سوى ${fmt(shares0)} سهم.`
    : type === "BUY" && cashCtx && (Number(f.shares) * Number(f.price)) > availCash
      ? `السيولة المتاحة ${fmt(availCash)} لا تكفي.`
    : null;
  const valid = baseValid && !blockReason;

  const preview: { label: string; value: string } | null =
    (type === "BUY" || type === "SELL") && Number(f.shares) > 0 && Number(f.price) > 0
      ? { label: tr("port.txTotal"), value: fmt(Number(f.shares) * Number(f.price)) }
    : type === "DIVIDEND" && Number(f.amount) > 0
      ? { label: "يُضاف إلى السيولة", value: fmt(Number(f.amount)) }
    : type === "BONUS" && Number(f.shares) > 0
      ? { label: "أسهمك بعد المنحة", value: fmt(shares0 + Number(f.shares)) }
    : type === "SPLIT" && Number(f.factor) > 0
      ? { label: "أسهمك بعد التجزئة", value: fmt(shares0 * Number(f.factor)) }
    : null;

  const hint: Record<string, string> = {
    BUY: "يُخصم الإجمالي من السيولة المتاحة. وسم «إعادة استثمار» يُنقص رصيد إعادة الاستثمار في التوازن التالي",
    SELL: "يُضاف صافي البيع إلى السيولة المتاحة تلقائياً",
    DIVIDEND: "يُضاف المبلغ إلى السيولة وإلى إجمالي التوزيعات",
    BONUS: "تُضاف الأسهم مجاناً وينخفض متوسط التكلفة تلقائياً. سعر يوم المنح يُثبّت قيمتها في العائد المحقّق — بدونه تُقدَّر بالسعر الأخير فتتحرّك مع السوق",
    SPLIT: "مثال: معامل 2 يعني كل سهم يصبح سهمين والسعر ينخفض للنصف",
  };

  return (
    <Modal title={`معاملة — ${company.name_ar || company.name}`} onClose={onClose}>
      <div className="space-y-3">
        {/* **مرآةٌ لجدول التوزيع النسبي، لا قراءةٌ ثانية له.**
            كان الجدول يعرض «سيولة» و«إعادة استثمار» بعدد **الأسهم**، وهذه
            البطاقة تعرضهما بالـ**ريال** تحت التسميتين نفسيهما — كمّيّتان
            مختلفتان باسمٍ واحد في شاشتين، وهو ما رآه المالك. الآن الحساب
            والوحدة والتقريب من الجدول نفسه حرفياً:
              المبلغ = round(سيولة) + round(إعادة)  ·  الأسهم = ⌊المبلغ ÷ السعر⌋
            ومتوسط التكلفة بمنزلتيه كما في صفحة الحيازات (23.66 لا 24):
            تقريبُه إلى رقمٍ صحيح يُخفي فرقاً يُحسب عليه قرار الشراء. */}
        <div className="tx-context grid grid-cols-3 gap-2 text-center">
          <div><p className="text-[10px] text-[var(--ink-muted)]">أسهمك</p><p className="text-xs font-bold text-[var(--ink)] tabular-nums">{fmt(holdingCtx?.total_shares ?? 0)}</p></div>
          <div><p className="text-[10px] text-[var(--ink-muted)]">متوسط التكلفة</p><p className="text-xs font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt2(holdingCtx?.average_cost ?? 0)}</p></div>
          <div>
            <p className="text-[10px] text-[var(--ink-muted)]">نصيبه من التوازن</p>
            {!myAlloc || !Number(myAlloc.target_weight) ? (
              <p className="text-xs font-bold text-[var(--ink-muted)]">لم يُحدَّد</p>
            ) : (() => {
              const liq = Number(myAlloc.liquidity_share) || 0;
              const rei = Number(myAlloc.reinvest_share) || 0;
              const lp  = Number(myAlloc.last_price) || 0;
              const total = Math.round(liq) + Math.round(rei);
              const shr = (v: number) => lp > 0 ? Math.floor(v / lp) : 0;
              return (
                <div className="space-y-0.5">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[9.5px] text-[var(--ink-muted)]">المبلغ</span>
                    <span className="text-[10px] font-bold tabular-nums" dir="ltr">{fmt(total)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[9.5px] text-[var(--ink-muted)]">سيولة</span>
                    <span className="text-[10px] font-bold tabular-nums" dir="ltr" style={{ color: "var(--pos-ink)" }}>{shr(liq).toLocaleString("en-US")} سهم</span>
                  </div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[9.5px] text-[var(--ink-muted)]">إعادة استثمار</span>
                    <span className="text-[10px] font-bold tabular-nums" dir="ltr" style={{ color: "var(--brand-ink)" }}>{shr(rei).toLocaleString("en-US")} سهم</span>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
        <Field label={tr("port.txType")}>
      <div className="grid grid-cols-3 gap-2">
            {TX_TYPES.map(t => (
              <button key={t.id} onClick={() => changeType(t.id)}
                className="py-2 rounded-xl text-xs font-bold transition-all"
                style={type === t.id
                  ? { background: mixA(t.color, 13), color: t.color }
                  : { background: "transparent", color: "var(--ink-muted)" }}>
                {t.label}
              </button>
            ))}
          </div>
          {type === "BUY" && (
            <div className="grid grid-cols-2 gap-2 mt-2">
              {FUNDING_SOURCES.map(s => (
                <button key={s.id} onClick={() => setFundingSource(s.id)}
                  className="py-1.5 rounded-lg text-[11px] font-bold transition-all"
                  style={fundingSource === s.id
                    ? { background: mixA(s.color, 13), color: s.color }
                    : { background: "transparent", color: "var(--ink-muted)" }}>
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </Field>

        {(type === "BUY" || type === "SELL") && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="عدد الأسهم"><NumInput value={f.shares} onChange={updV("shares")} allowDecimal={false} placeholder="0" /></Field>
            <Field label="سعر السهم"><NumInput value={f.price} onChange={updV("price")} placeholder="0.00" /></Field>
          </div>
        )}
        {type === "DIVIDEND" && (
          <Field label="مبلغ التوزيع الإجمالي"><NumInput value={f.amount} onChange={updV("amount")} placeholder="0.00" /></Field>
        )}
        {type === "BONUS" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="عدد أسهم المنحة"><NumInput value={f.shares} onChange={updV("shares")} allowDecimal={false} placeholder="0" /></Field>
            <Field label="سعر السهم يوم المنح"><NumInput value={f.price} onChange={updV("price")} placeholder="اختياري" /></Field>
          </div>
        )}
        {type === "SPLIT" && (
          <>
            <Field label="معامل التجزئة"><NumInput value={f.factor} onChange={updV("factor")} placeholder="2" /></Field>
            {/* التجزئة تضرب كل أسهمك المملوكة وقتها. ومن يقرأ كمياته من تطبيق
                الوسيط يقرأها مُجزَّأةً أصلاً، فتُضرب مرّتين وتفسد الحيازة صامتة.
                إقرارٌ صريح بدل تخمينٍ يُفسد البيانات. */}
            <label className="flex items-start gap-2 text-[11px] leading-relaxed cursor-pointer rounded-xl p-3"
              style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
              <input type="checkbox" className="mt-0.5" checked={preSplitOk}
                onChange={e => setPreSplitOk(e.target.checked)} />
              <span className="text-[var(--ink)]">
                أُقرّ بأن كميات العمليات المسجَّلة قبل هذا التاريخ هي كميات <b>ما قبل التجزئة</b>.
                <span className="block text-[var(--ink-muted)] mt-0.5">
                  إن كنت أدخلت كمياتك كما تظهر في تطبيق الوسيط اليوم فهي مُجزَّأة أصلاً، ولا تُسجَّل التجزئة مرّةً أخرى.
                </span>
              </span>
            </label>
          </>
        )}

        {/* لا تاريخ مستقبلي: يُقفل في المتصفح أيضاً لا في الخادم وحده. */}
        <Field label={tr("port.txDate")}><input className="input" type="date" lang="en" max={new Date().toISOString().slice(0, 10)} value={f.date} onChange={upd("date")} /></Field>

        <div className="panel rounded-xl p-3 text-xs text-[var(--ink-muted)]">{hint[type]}</div>

        {/* معاينة الأثر قبل التأكيد — لكل الأنواع لا للشراء والبيع وحدهما.
            التجزئة خصوصاً تغيّر عدد أسهمك وسعرها، ورؤيتها بعد التنفيذ متأخّرة. */}
        {/* متوسط التكلفة بعد هذه الصفقة — يُحسب لحظياً من حيازتك ومدخلاتك،
            فترى أثر السعر الجديد على تكلفتك قبل التنفيذ لا بعده. */}
        {type === "BUY" && Number(f.shares) > 0 && Number(f.price) > 0 && (
          <div className="panel rounded-xl p-3 text-sm flex items-center justify-between gap-3">
            <span className="text-[var(--ink-muted)]">متوسط التكلفة الجديد</span>
            <span className="text-[var(--brand-ink)] font-bold tabular-nums" dir="ltr">
              {fmt(newAvgCost)} <span className="text-[11px] text-[var(--ink-muted)]">(الآن {fmt(Number(holdingCtx?.average_cost ?? 0))})</span>
            </span>
          </div>
        )}
        {preview && (
          <div className="panel rounded-xl p-3 text-sm flex items-center justify-between gap-3">
            <span className="text-[var(--ink-muted)]">{preview.label}</span>
            <span className="text-[var(--ink)] font-bold tabular-nums" dir="ltr">{preview.value}</span>
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button className="btn-primary flex-1" onClick={() => mutation.mutate()} disabled={mutation.isPending || !valid}>
            {mutation.isPending ? tr("port.processing") : tr("port.confirmTx")}
          </button>
          <button className="btn-ghost" onClick={onClose}>{tr("common.cancel")}</button>
        </div>
        {blockReason && baseValid && <p className="text-[var(--warn-ink)] text-xs">{blockReason}</p>}
        {mutation.isError && <p className="text-[var(--neg-ink)] text-xs">{(mutation.error as any)?.response?.data?.detail || tr("common.error")}</p>}
      </div>
    </Modal>
  );
}

// ── Cash Deposit / Withdraw (الضخ الشهري) ────────────────────
function CashModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [mode, setMode] = useState<"deposit" | "withdraw">("deposit");
  const [amount, setAmount] = useState("");
  const { data: cash } = useQuery({ queryKey: ["cash"], queryFn: () => cashApi.get().then(r => r.data?.data) });
  const { data: history = [], isLoading: histLoading } = useQuery({
    queryKey: ["cash-history"],
    queryFn: () => cashApi.history(50).then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
  const mutation = useMutation({
    mutationFn: () => (mode === "deposit"
      ? cashApi.deposit({ amount: Number(amount) })
      : cashApi.withdraw({ amount: Number(amount) })).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); setAmount(""); },
  });
  const deleteLedgerMut = useMutation({
    mutationFn: (id: number) => cashApi.removeLedger(id).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
  });
  const deleteTxMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => transactionsApi.remove(id, reason).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
  });
  const removeItem = (item: any) => {
    if (item.kind === "ledger") {
      if (confirm("حذف هذه الحركة النقدية؟")) deleteLedgerMut.mutate(item.id);
      return;
    }
    // العمليةُ المحذوفة تبقى في سجلّ التغييرات بصورتها وسببها (D481)
    const why = prompt("سبب حذف هذه العملية؟ سيُعكس أثرها على السيولة والمركز، وتبقى في سجلّ التغييرات.");
    if (why !== null) deleteTxMut.mutate({ id: item.id, reason: why });
  };
  return (
    <Modal title="السيولة النقدية" onClose={onClose}>
      <div className="space-y-4">
        {cash && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="kpi"><div className="kpi-lbl">السيولة المتاحة</div><div className="kpi-val">{fmt(cash.available_cash)}</div></div>
            <div className="kpi"><div className="kpi-lbl">إجمالي السيولة</div><div className="kpi-val">{fmt(cash.total_cash)}</div></div>
            {cash.pending_cash > 0 && <div className="kpi"><div className="kpi-lbl">سيولة معلّقة</div><div className="kpi-val">{fmt(cash.pending_cash)}</div></div>}
          </div>
        )}

        {isOwner && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setMode("deposit")} className="py-2 rounded-xl text-sm font-bold border"
                style={mode === "deposit" ? {background:"transparent",color:"var(--pos-ink)",borderColor:"color-mix(in srgb, var(--pos-ink) 40%, transparent)"} : {borderColor:"var(--hairline)",color:"var(--ink-muted)"}}>إيداع (ضخ)</button>
              <button onClick={() => setMode("withdraw")} className="py-2 rounded-xl text-sm font-bold border"
                style={mode === "withdraw" ? {background:"transparent",color:"var(--neg-ink)",borderColor:"color-mix(in srgb, var(--neg-ink) 40%, transparent)"} : {borderColor:"var(--hairline)",color:"var(--ink-muted)"}}>سحب</button>
            </div>
            <Field label="المبلغ"><NumInput value={amount} onChange={setAmount} placeholder="0.00" /></Field>
            <div className="flex gap-3">
              <button className="btn-primary flex-1" onClick={() => mutation.mutate()} disabled={mutation.isPending || !(Number(amount) > 0)}>تأكيد</button>
            </div>
        {mutation.isError && <p className="text-[var(--neg-ink)] text-xs">{(mutation.error as any)?.response?.data?.detail || "حدث خطأ"}</p>}
          </>
        )}

        <div className="border-t border-[var(--hairline)] pt-3">
          <p className="text-xs font-bold text-[var(--ink-muted)] mb-2">سجل حركة السيولة</p>
          {histLoading ? (
            <div className="h-20 skeleton" />
          ) : history.length === 0 ? (
            <p className="text-xs text-[var(--ink-muted)] py-4 text-center">لا توجد حركات مسجلة بعد</p>
          ) : (
            <div className="space-y-1.5 max-h-64 overflow-auto">
              {history.map((it: any) => (
                <div key={`${it.kind}-${it.id}`} className="flex items-center justify-between gap-2 p-2 rounded-lg panel">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-[var(--ink)] truncate">
                      {it.label}{it.company ? ` — ${it.company}` : ""}
                    </p>
                    <p className="text-[10px] text-[var(--ink-muted)]">{it.date ? new Date(it.date).toLocaleString("en-GB") : "—"}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={"text-xs font-bold tabular-nums " + (it.amount >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>
                      {it.amount >= 0 ? "+" : ""}{fmt(it.amount)}
                    </span>
                    {isOwner && (
                      <button onClick={() => removeItem(it)} disabled={deleteLedgerMut.isPending || deleteTxMut.isPending}
                        className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all">
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <button className="btn-ghost w-full" onClick={onClose}>إغلاق</button>
      </div>
    </Modal>
  );
}

// ── Edit Holding (shares / avg cost — for migrating an existing portfolio) ──
function HoldingModal({ holding, onClose }: { holding: any; onClose: () => void }) {
  const tr = useT();
  const qc = useQueryClient();
  const [qty, setQty] = useState(String(holding.quantity ?? holding.total_shares ?? ""));
  const [avg, setAvg] = useState(String(holding.average_cost ?? ""));
  const mutation = useMutation({
    mutationFn: () => holdingsApi.update(holding.company_id ?? holding.company?.id, {
      quantity: Number(qty), average_cost: Number(avg),
    }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); onClose(); },
  });
  return (
    <Modal title={`تعديل المركز — ${holding.company?.name_ar || holding.company?.name}`} onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="عدد الأسهم"><NumInput value={qty} onChange={setQty} allowDecimal={false} /></Field>
          <Field label="متوسط التكلفة"><NumInput value={avg} onChange={setAvg} /></Field>
        </div>
        {Number(qty) > 0 && Number(avg) > 0 && (
          <div className="panel rounded-xl p-3 text-sm">
            <span className="text-[var(--ink-muted)]">إجمالي المستثمر: </span>
            <span className="text-[var(--ink)] font-bold">{(Number(qty) * Number(avg)).toLocaleString("en-US")}</span>
          </div>
        )}
        {Math.abs(Number(holding.cost_basis_adjustment || 0)) > 0.01 && (
          <div className="rounded-xl p-3 text-[11px] leading-relaxed"
            style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
            <span className="text-[var(--ink-muted)]">فارق تسوية محفوظ مقابل سجل العمليات: </span>
            <span className="font-bold tabular-nums text-[var(--ink)]" dir="ltr">
              {Number(holding.cost_basis_adjustment) > 0 ? "+" : ""}
              {Number(holding.cost_basis_adjustment).toLocaleString("en-US", { maximumFractionDigits: 2 })}
            </span>
            <span className="text-[var(--ink-muted)]"> — تكلفتك المعتمدة أعلى/أدنى من مجموع عملياتك المسجّلة بهذا المقدار، ويُحفَظ الفارق كي لا تمحوه إعادة بناء الحيازة عند أي تعديل لاحق.</span>
          </div>
        )}
        <p className="text-[11px] text-[var(--warn-ink)]">تصحيح مباشر للمركز فقط — لا يُنشئ عملية في سجل العمليات ولا يؤثر على السيولة. لتسجيل شراء/بيع فعلي يعكس أثره على السيولة استخدم زر "شراء/بيع" بدلاً من هذا.</p>
        <div className="flex gap-3 pt-1">
          <button className="btn-primary flex-1" onClick={() => mutation.mutate()} disabled={mutation.isPending || !qty || !avg}>
            {mutation.isPending ? tr("common.saving") : tr("common.save")}
          </button>
          <button className="btn-ghost" onClick={onClose}>{tr("common.cancel")}</button>
        </div>
        {mutation.isError && <p className="text-[var(--neg-ink)] text-xs">{tr("common.error")}</p>}
      </div>
    </Modal>
  );
}

// ── Delete Confirm ────────────────────────────────────────────
function DeleteModal({ company, onClose }: { company: any; onClose: () => void }) {
  const tr = useT();
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => companiesApi.remove(company.id).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); onClose(); },
  });
  return (
    <Modal title={tr("port.deleteCompany")} onClose={onClose}>
      <p className="text-[var(--ink)] mb-6">{tr("port.deleteConfirm")} <strong className="text-[var(--ink)]">{company.name_ar || company.name}</strong>{tr("port.deleteWarn")}</p>
      <div className="flex gap-3">
        <button className="btn-danger flex-1" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
          {mutation.isPending ? tr("port.deleting") : tr("port.yesDelete")}
        </button>
        <button className="btn-ghost flex-1" onClick={onClose}>{tr("common.cancel")}</button>
      </div>
    </Modal>
  );
}

// ── Portfolio Financial Metrics (المؤشرات المالية للمحفظة) ────
/* تسع خانات في ثلاثة صفوف، كلُّ صفٍّ سؤالٌ واحد:
     ١) ماذا تُنتج المحفظة وإلى أين تتّجه؟  (عائد التوزيعات · اتجاه المحللين · النمو المركّب)
     ٢) ماذا دخل جيبك فعلاً؟               (التصفية · التوزيعات · المنحة)
     ٣) كيف هي مسعَّرة وكم منها يعمل؟      (مكرر الربحية · نسبة التوظيف · …)
   وصفُّ الإنتاج بمبالغ صريحة لا نِسب: الأخضر لما دخل نقداً (توزيعات وتصفية)،
   والأزرق للمنحة لأنها ورقٌ لا نقد — بقيمتها السوقية لا بعددها، فالعدد وحده
   لا يقول شيئاً عن قيمته. واختلاف اللون هو ما يمنع جمعها في الذهن مع النقد. */
function PortfolioMetricsCard() {
  const { data: m } = useQuery({ queryKey: ["portfolio-metrics"], queryFn: () => portfolioApi.metrics().then(r => r.data.data), retry: 0 });
  const { data: s } = useQuery({ queryKey: ["portfolio-summary"], queryFn: () => portfolioApi.summary().then((r: any) => r.data.data), retry: 0 });
  if (!m) return null;
  const pct = (v: any, d = 1) => v == null ? null : (v >= 0 ? "+" : "") + Number(v).toFixed(d) + "%";
  const growth: number | null = s?.capital_growth_pct ?? null;

  type Cell = { lbl: string; val: string | null; color?: string };
  const cells: Cell[] = [
    { lbl: "عائد التوزيعات", val: m.dividend_yield != null ? m.dividend_yield.toFixed(1) + "%" : null },
    { lbl: "اتجاه المحللين", val: pct(m.analyst_upside_pct) },
    // العائد المركّب يبقى في مكانه اسماً دائماً؛ وقبل ٩٠ يوماً من أوّل ضخّ لا
    // رقم له (ضربُ شهرٍ في اثني عشر يَعِد بما لا يُعرف) فيُعرض العائد منذ
    // البداية تحته بمدّته بدل أن تختفي الخانة ويتزحزح الصفّ.
    { lbl: "العائد المركّب", val: pct(m.cagr_pct, 2) },

    { lbl: "التصفية", val: s ? fmt(s.sale_gains ?? 0) : null, color: "var(--pos-ink)" },
    { lbl: "التوزيعات", val: s ? fmt(s.dividends_received ?? 0) : null, color: "var(--pos-ink)" },
    { lbl: "المنحة", val: s ? fmt(s.bonus_market_value ?? 0) : null, color: "var(--info-ink)" },

    // مكرر الربحية مقارناً بوسيط السوق: رقمٌ مجرّد لا يُعرف أمرتفعٌ هو أم
    // منخفض، والوسيط محسوبٌ سلفاً في صفوف الفرز المخزَّنة بلا نداء.
    { lbl: "مكرر الربحية", val: m.pe_ratio != null ? m.pe_ratio.toFixed(2) : null },
    { lbl: "نسبة التوظيف", val: m.deployed_pct != null ? m.deployed_pct.toFixed(1) + "%" : null },
    // الخانة التاسعة: أين حيازاتك من قمّتها السنوية — سؤال «أأضخّ الآن؟»،
    // وهو القرار الذي يتكرّر شهرياً في محفظةٍ أغلبها نقدٌ ينتظر.
    // تتلوّن دائماً بتدرّج معناها: كلما ابتعدت عن القمّة اتّسعت مسافة الصعود.
    { lbl: "عن قمّة ٥٢ أسبوعاً", val: pct(m.off_high_pct, 1),
      /* قيمٌ سداسية مصمَّمة للمظهر الداكن كانت 1.75:1 على الورق الفاتح —
         أضعف نصٍّ في الشاشة. الرموز مضبوطة للمظهرين. */
      color: m.off_high_pct == null ? undefined
        : m.off_high_pct <= -10 ? "var(--pos-ink)"
        : m.off_high_pct <= -5 ? "var(--warn-ink)" : "var(--neg-ink)" },
  ];
  /* الخانة الغائبة تُعرض شرطةً ولا تُحذف: حذفُها يُزحزح ما بعدها فينكسر
     ترتيب الصفوف الثلاثة ويقفز مؤشّرٌ من صفٍّ إلى آخر بين زيارتين. */
  if (!cells.some(c => c.val != null)) return null;
  const shown = cells;

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp size={15} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">المؤشرات المالية للمحفظة</h2>
        <span className="text-[11px] text-[var(--ink-muted)] mr-auto">{m.companies_covered} شركة</span>
      </div>
      {/* **عائد المحفظة** — النسبة الموحّدة نفسها (صافي الربح ÷ إجمالي
          المدفوع) التي يعرضها باند الثروة مبلغاً والأهداف شريطاً. رقمٌ واحد في
          ثلاثة مواضع لا ثلاثة أرقام متقاربة، ونظيفٌ بلا تفصيلٍ تحته. */}
      {growth != null && (
        <div className="rounded-xl p-3 mb-2.5"
          style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
          <div className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--ink-muted)" }}>عائد المحفظة</div>
          <div className={"text-xl font-extrabold tabular-nums " + (growth >= 0 ? "profit" : "loss")} dir="ltr"
            style={{ textAlign: "right" }}>
            {(growth >= 0 ? "+" : "") + growth.toFixed(2)}%
          </div>
        </div>
      )}
      <div className="grid grid-cols-3 gap-2">
        {shown.map(c => (
          <div key={c.lbl} className="kpi">
            <div className="kpi-lbl">{c.lbl}</div>
            {/* الرقم بمحاذاة اليمين كالتسمية فوقه: العربية تبدأ من اليمين،
                و`dir=ltr` للرقم وحده كي تبقى الإشارة والنسبة في موضعهما. */}
            <div className="kpi-val tabular-nums" dir="ltr" style={{ textAlign: "right", color: c.val == null ? "var(--ink-muted)" : c.color }}>{c.val ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── مراجعة أوسمة التمويل ─────────────────────────────────────────────
   الوسم تصنيفٌ يدوي لا واقعة تُثبت، فيخطئ. والخطأ هنا ليس رأياً يُختلف فيه:
   شراءٌ موسوم «إعادة استثمار» بمبلغٍ يفوق ما كان في الحوض **يوم تنفيذه**
   مستحيلٌ حسابياً — لا يُنفَق مالٌ لم يدخل الحساب بعد.

   وأثره ليس تجميلياً: يُبخّس حوض إعادة الاستثمار (فيظهر صفراً بلا سبب مرئي)،
   ويرفع «عائد المحفظة» بتخفيض مقامه، لأن رأس المال المدفوع يطرح المُعاد ضخّه.

   ولا يُصلَح شيءٌ تلقائياً: تُعرض الوقائع ويقرّر المالك. وإزالة الوسم لا تمسّ
   نقداً ولا كميةً ولا تكلفة (كل شراءٍ يخصم نقده بنفس الطريقة مهما كان مصدره
   المفترض)، فهي آمنةٌ بالكامل وقابلة للتراجع من تحرير العملية. */
function TagAudit() {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["tag-audit"],
    queryFn: () => transactionsApi.tagAudit().then(r => r.data.data),
    retry: 0,
  });
  const untag = useMutation({
    mutationFn: (ids: number[]) => transactionsApi.untag(ids).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries();   // نفس القاعدة: كتابةٌ ⇐ إبطالٌ شامل
    },
  });

  const items = data?.items ?? [];
  if (!items.length) return null;

  return (
    <div className="rounded-xl p-3 mb-3"
      style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
      <div className="flex items-center gap-2 flex-wrap">
        <AlertTriangle size={14} className="text-[var(--warn-ink)]" />
        <span className="text-[12.5px] font-bold text-[var(--warn-ink)]">
          {items.length} وسم إعادة استثمار يتجاوز رصيد الحوض وقت التنفيذ
        </span>
        <button className="btn-ghost text-[11px] mr-auto" onClick={() => setOpen(o => !o)}>
          {open ? "إخفاء" : "عرض التفاصيل"}
        </button>
      </div>
      <p className="text-[11px] text-[var(--ink-muted)] mt-1.5">
        الفائض المتعذّر <b className="text-[var(--warn-ink)] tabular-nums" dir="ltr">{fmt(data.total_excess)}</b>
      </p>

      {open && (
        <div className="mt-2.5 space-y-1.5">
          {items.map((it: any) => (
            <div key={it.id} className="rounded-lg p-2 flex items-center gap-2 flex-wrap"
              style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
              <div className="min-w-0">
                <p className="text-[12px] text-[var(--ink)] font-semibold">{it.company}</p>
                <p className="text-[10.5px] text-[var(--ink-muted)]" dir="ltr">{it.date}</p>
              </div>
              <div className="text-[10.5px] text-[var(--ink-muted)] leading-tight">
                <p>المبلغ <span className="tabular-nums text-[var(--ink)]" dir="ltr">{fmt(it.amount)}</span></p>
                <p>الحوض وقتها <span className="tabular-nums text-[var(--ink)]" dir="ltr">{fmt(it.pool_at_time)}</span></p>
              </div>
              <div className="text-[10.5px] leading-tight">
                <p className="text-[var(--ink-muted)]">فائض متعذّر</p>
                <p className="tabular-nums font-bold text-[var(--warn-ink)]" dir="ltr">{fmt(it.excess)}</p>
              </div>
              {isOwner && (
                <button className="btn-ghost text-[11px] mr-auto"
                  onClick={() => untag.mutate([it.id])} disabled={untag.isPending}>
                  أزِل الوسم
                </button>
              )}
            </div>
          ))}
          {isOwner && (
            <button className="btn-primary w-full text-[12px]"
              onClick={() => untag.mutate(items.map((i: any) => i.id))} disabled={untag.isPending}>
              {untag.isPending ? "جارٍ…" : `أزِل الوسم عن الـ${items.length} كلّها`}
            </button>
          )}

        </div>
      )}
    </div>
  );
}

// ── Target Weights & Rebalance (advisory only) ───────────────
export function RebalanceCard() {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [targets, setTargets] = useState<Record<number, string>>({});
  const [showProfit, setShowProfit] = useState(false);
  /* ══ اسمُ الشركة يفتح ورقتَها ══ (بأمر المالك · D207)
     الجدولُ يعرض شركاتِ المحفظة ولا يُفضي إليها، فمن أراد قراءةَ حال
     شركةٍ قبل تعديل وزنها غادر البطاقةَ وبحث عنها. والورقةُ هي نفسُها
     التي يفتحها قسمُ السوق وخريطةُ القطاعات — لا شاشةٌ رابعة. */
  const [sheet, setSheet] = useState<string | null>(null);

  const { data: alloc } = useQuery({
    queryKey: ["allocation"],
    queryFn: () => allocationApi.get().then(r => r.data.data),
  });
  /* «اقتراح إعادة التوازن» أُلغي بقرار المالك. كان يحسب نصيب الشركة بمذهبٍ
     آخر تماماً: الفجوة بين وزنها المستهدف وقيمتها السوقية (delta)، ثم
     `min(delta, وزنها × حوض التوزيعات)` — بينما «التوزيع النسبي» وبطاقة
     المعاملة يحسبان النصيب حصّةً من النقد بحسب الوزن. مذهبان مختلفان على
     الشاشة نفسها يعطيان رقمين مختلفين للشركة الواحدة، وهو مصدر «الأرقام
     الفوضوية». الآن أساسٌ واحد: التوزيع النسبي. */
  /* البطاقة تُفتح وتُغلق كثيراً، فتُبقى نتيجتها في الذاكرة دقيقةً كاملة:
     الفتحة الثانية تظهر فوراً بدل انتظار الشبكة من جديد. */
  const { data: profitData, isFetching: profitLoading, isError: profitError,
          refetch: refetchProfit } = useQuery({
    queryKey: ["profit-liquidation"],
    queryFn: () => allocationApi.profitLiquidation().then(r => r.data.data),
    enabled: showProfit,
    staleTime: 60_000,
    retry: 1,
  });
  /* العتبة تُحرَّر نصّاً وتُحفظ بزرّ: حفظُ كل ضغطة يعيد حساب المحفظة كلّها،
     والرقم يُكتب على مرحلتين («2» ثم «25»). */
  const [thrDraft, setThrDraft] = useState("20");
  useEffect(() => {
    if (profitData?.threshold_pct != null) setThrDraft(String(profitData.threshold_pct));
  }, [profitData?.threshold_pct]);
  const saveThreshold = useMutation({
    mutationFn: (v: number) => allocationApi.setLiquidationThreshold(v).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
  });
  /* عتبة الشركة الواحدة — تُحفظ فور تركِ الحقل: صفٌّ واحد في الخادم، ولا
     معنى لزرِّ حفظٍ لكل مركز. */
  /* نصّ عتبة كل شركة أثناء الكتابة: «5» ثم «50» رقمان، وحفظ الأول يُعيد
     حساب المحفظة بلا داعٍ. يُحفظ عند ترك الحقل. */
  const [thrRow, setThrRow] = useState<Record<number, string>>({});
  /* المجموعُ المستهدف — تفضيلُ عرضٍ لهذا الجهاز، لا بيانَ محفظةٍ يُحفظ في
     الخادم: لا يدخل في حسابِ نصيبٍ ولا في أمرِ شراء، وإنما يقول للوسم
     متى يكون أخضر. */
  const [deployDraft, setDeployDraft] = useState<string>(() => {
    try { return localStorage.getItem("sp.deployTarget") || "100"; } catch { return "100"; }
  });
  useEffect(() => {
    try { localStorage.setItem("sp.deployTarget", deployDraft); } catch { /* وضعُ التصفّح الخاصّ */ }
  }, [deployDraft]);
  const saveCompanyThr = useMutation({
    mutationFn: (v: { id: number; pct: number | null }) =>
      allocationApi.setCompanyThreshold(v.id, v.pct).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
  });
  const saveMutation = useMutation({
    mutationFn: () => allocationApi.setTargets(
      Object.entries(targets).map(([id, w]) => ({ company_id: Number(id), target_weight: Number(w) || 0 }))
    ).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); },
  });

  const items = alloc?.items ?? [];
  if (!items.length) return null;
  const val = (id: number, fallback: number) => targets[id] !== undefined ? targets[id] : String(fallback || "");
  const sumTargets = items.reduce((a: number, it: any) => a + (Number(val(it.company_id, it.target_weight)) || 0), 0);
  /* ══ المجموعُ المستهدف ليس مئةً بالضرورة ══ (بأمر المالك)
     مَن أراد أن يوزّع سبعين بالمئة ويُبقي ثلاثين نقداً كان يرى وسمَ المجموع
     محذّراً برتقالياً وهو مصيبٌ في قصده. فصار الهدفُ رقماً يكتبه، والوسمُ
     يُقاس عليه. ولا أثرَ له في الحساب: النصيبُ أصلاً `وزن ÷ 100 × النقد`،
     فمجموعُ سبعين ينشر سبعين بالمئة ويترك الباقيَ نقداً من نفسه. */
  const deployTarget = Number(deployDraft) || 0;
  const retainedPct = retainedCashPct(deployTarget);
  /* تطبيقُ المجموع المستهدف: تنزل الأوزانُ كلُّها بنسبةٍ واحدة فيبلغ مجموعُها
     الرقمَ المكتوب، وتتبعها المبالغُ والأسهم لأنها تُحسب من الحقول نفسها.
     ويبقى الأمرُ **معاينةً** حتى يُضغط الحفظ — كبقيّة تعديلات هذه البطاقة. */
  const applyDeployTarget = () => {
    const t = Number(deployDraft);
    if (!isFinite(t) || t <= 0 || t > 100) return;
    const ids = items.map((it: any) => it.company_id);
    const cur = items.map((it: any) => Number(val(it.company_id, it.target_weight)) || 0);
    if (!(cur.reduce((a: number, b: number) => a + b, 0) > 0)) return;
    const next = rescaleWeights(cur, t);
    setTargets(s => {
      const o = { ...s };
      ids.forEach((id: number, i: number) => { o[id] = String(next[i]); });
      return o;
    });
  };
  /* معدّلُ عائد التوزيعات مرجّحاً بالأوزان المكتوبة الآن — يتحرّك مع كلّ
     تعديل قبل الحفظ، كبقيّة أرقام هذه البطاقة. وشركةٌ بلا عائدٍ معلوم تخرج
     من البسط والمقام معاً، فلا تُقرأ صفراً. */
  const dyAgg = weightedDividendYield(
    items, (it: any) => Number(val(it.company_id, it.target_weight)) || 0);
  const dyWeighted = dyAgg.value;
  /* هل في الحقول وزنٌ يخالف المحفوظ؟ عليه يتوقّف وسم «معاينة» أعلى البطاقة. */
  const hasUnsaved = items.some((it: any) =>
    (Number(val(it.company_id, it.target_weight)) || 0) !== (Number(it.target_weight) || 0));

  /* نصيب كل شركة من السيولة ومن رصيد إعادة الاستثمار — بنسبة وزنها المستهدف
     مباشرةً من باند الثروة، لا بحصّة حاجتها. يُحسب هنا محليّاً من الوزن
     المكتوب في الحقل الآن (حتى قبل الحفظ) فترى الأثر فوراً وأنت تعدّل الرقم —
     نفس أسلوب «المتبقي للهدف» السابق. شركة بلا وزن ⇐ لا حصّة، «لم تحدد». */
  /* «سيولة» تعني النقد الجديد (النقد ناقص الحوض) لا النقد الكامل: الحوض جزءٌ
     من النقد، فحسابُ النصيبين على النقد الكامل يعدّ الحوض مرّتين ويُظهر مبلغاً
     شرائياً أكبر من المتاح. الآن سيولة + إعادة استثمار = النقد المتاح بالضبط. */
  const pool = alloc?.reinvestment_pool || 0;
  const availCash = alloc?.fresh_cash ?? Math.max(0, (alloc?.available_cash || 0) - pool);
  const shareOf = (it: any) => {
    const tw = Number(val(it.company_id, it.target_weight)) || 0;
    /* ══ الحسابُ في `allocMath.rebalanceRow` ══ (D217)
       كان النصيبُ يُحسب هنا بالوزن المستهدف وحدَه بلا نظرٍ إلى الحاليّ،
       فالشركةُ المتضخّمةُ تأخذ نصيباً جديداً فيزداد اختلالُها، ولا يظهر
       رقمٌ سالبٌ يقول «بِعْ». والقاعدةُ الآن دالّةٌ خالصةٌ يفحصها الحارس. */
    const rb = rebalanceRow({
      currentWeight: Number(it.current_weight) || 0,
      targetWeight: tw,
      investable: (alloc?.total_market_value || 0) + (alloc?.available_cash || 0),
      lastPrice: Number(it.last_price) || 0,
      freshCash: availCash,
      reinvestPool: pool,
    });
    if (rb.side === "sell") {
      return { tw, liquidityShare: null, reinvestShare: null,
               totalAmount: Math.round(rb.totalAmount as number),
               totalShares: rb.totalShares, side: "sell" as const,
               excessPct: rb.excessPct };
    }
    if (rb.side === "none") {
      return { tw, liquidityShare: null, reinvestShare: null, totalAmount: null,
               totalShares: null, side: "none" as const, excessPct: rb.excessPct };
    }
    const liquidityShare = rb.liquidityShare as number;
    const reinvestShare = rb.reinvestShare as number;
    /* **المجموع هو جمع ما تراه.** المبالغ تُعرض بلا كسور، وجزآ أرامكو
       ١٧٬٤٠٤٫٦١ و٣٦٠٫٦٦ يُعرضان ١٧٬٤٠٥ و٣٦١ فيجمعان ١٧٬٧٦٦، بينما مجموعهما
       الحقيقي ١٧٬٧٦٥٫٢٧ يُعرض ١٧٬٧٦٥. ريالٌ واحد، لكنه رقمٌ يخالف نفسه بين
       بطاقة التوزيع وبطاقة المعاملة — ومن رأى ذلك مرّةً شكّ في الأرقام
       كلّها. يُجمع المعروضان لا الخامان، فلا يبقى فرق. */
    const totalAmount = Math.round(liquidityShare) + Math.round(reinvestShare);
    const totalShares = it.last_price > 0 ? totalAmount / it.last_price : null;
    return { tw, liquidityShare, reinvestShare, totalAmount, totalShares,
             side: "buy" as const, excessPct: rb.excessPct };
  };
  /* تحويل مبلغٍ إلى أسهم بسعر الشركة الأخير — الأسهم وحدة القرار الفعلية:
     المالك يشتري أسهماً لا مبالغ، وقراءة «١٢٬٤٠٠ ريال» تحتاج قسمةً ذهنية على
     سعر السهم قبل أن تصير أمراً قابلاً للتنفيذ. */
  /* أسهم صحيحة لا كسور: تداول لا يقبل جزء سهم، فعرض «12.4 سهماً» ليس أمراً
     قابلاً للتنفيذ. يُقرَّب للأسفل كي لا يتجاوز الأمرُ المبلغَ المتاح. */
  const shrOf = (amount: number | null, it: any) =>
    (amount != null && it.last_price > 0) ? Math.floor(amount / it.last_price) : 0;
  /* مجاميع الأعمدة — الجدول بلا مجموع يترك المالك يجمع بنفسه ليتحقّق أن
     النصيبين يساويان ما لديه فعلاً. */
  const totals = items.reduce((a: any, it: any) => {
    const { tw, liquidityShare, reinvestShare, totalAmount } = shareOf(it);
    if (tw > 0) {
      a.amount += totalAmount || 0;
      a.liq += liquidityShare || 0;
      a.rei += reinvestShare || 0;
      a.liqShares += shrOf(liquidityShare, it);
      a.reiShares += shrOf(reinvestShare, it);
    }
    return a;
  }, { amount: 0, liq: 0, rei: 0, liqShares: 0, reiShares: 0 });

  /* ══ دخلُ التوزيعات: ما هو اليوم، وما يصير بعد التوظيف ══
     (بأمر المالك · D190)
     الجدولُ كان يقول كم سهماً يُشترى ولا يقول ماذا يُدرّ. والرقمان:
       · الحاليّ  = Σ (قيمةُ المركز السوقية × عائدُ توزيعاته)
       · المستهدف = Σ ((القيمة + نصيبُها من النقد) × العائد نفسِه)
     أي دخلُ سنةٍ كاملةٍ بأسعار اليوم وتوزيعاتِ آخر اثني عشر شهراً — لا
     تنبّؤَ بزيادةٍ ولا نقصان. والشركةُ بلا عائدٍ معلومٍ لا تُحسب صفراً:
     تُعدّ ويُقال عددُها، فالمعروضُ حدٌّ أدنى مصرَّحٌ به لا رقمٌ ناقصٌ صامت. */
  const income = items.reduce((a: any, it: any) => {
    const dy = it.dividend_yield;
    const mv = Number(it.market_value) || 0;
    const { totalAmount } = shareOf(it);
    if (typeof dy === "number" && isFinite(dy)) {
      a.now += mv * dy / 100;
      a.after += (mv + (totalAmount || 0)) * dy / 100;
    } else if (mv > 0 || totalAmount) {
      a.unknown += 1;
    }
    return a;
  }, { now: 0, after: 0, unknown: 0 });

  return (
    <div className="card">
      <TagAudit />
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Scale size={15} className="text-[var(--brand-ink)]" />
          <h2 className="card-title">التوزيع النسبي</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className={"text-xs font-bold " + (Math.abs(sumTargets - deployTarget) < 0.01 ? "text-[var(--pos-ink)]" : "text-[var(--warn-ink)]")}>المجموع: {sumTargets.toFixed(1)}%</span>
          <span className="flex items-center gap-1 text-xs text-[var(--ink-muted)]">
            من
            {/* يُطبَّق عند ترك الحقل أو بالإدخال — لا مع كلّ ضغطة: «70» تُكتب
                «7» أوّلاً، فإعادةُ التوزيع على سبعةٍ تمحو الأوزان قبل أن
                يُتمّ المالكُ رقمَه. */}
            <input className="input tabular-nums" style={{ width: 56, padding: "4px 8px" }}
              type="text" inputMode="decimal" lang="en" dir="ltr"
              title="المجموع المستهدف — تُعاد الأوزان بنسبها، وما تبقّى يبقى نقداً"
              aria-label="المجموع المستهدف"
              value={deployDraft}
              onBlur={() => applyDeployTarget()}
              onKeyDown={e => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
              onChange={e => setDeployDraft(
                e.target.value
                  .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660))
                  .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x06F0))
                  .replace(/[^\d.]/g, ""))} />
            %
          </span>
          {retainedPct > 0 && (
            <span className="text-xs text-[var(--ink-muted)] tabular-nums" dir="rtl">
              يبقى نقداً {retainedPct.toFixed(0)}%
            </span>
          )}
          {/* **حمايةُ الرقم**: هذه البطاقة تحسب الأنصبة من الوزن المكتوب في
              الحقل الآن (معاينةً فوريّة)، بينما بطاقة المعاملة تقرأ الوزن
              **المحفوظ** من الخادم. فما دام في الحقول تعديلٌ لم يُحفظ، الرقمان
              مختلفان بحقّ — لا خطأ. يُقال ذلك صراحةً بدل أن يُترك المالك
              يوازن بين رقمين لا يعرف أيّهما الأساس. */}
          {hasUnsaved && (
            <span className="unsaved-tag">معاينة — أوزانٌ غير محفوظة</span>
          )}
          {/* الترتيب في اتجاه الصفحة (يمين ← يسار): التصفية ثم الحفظ، فيقع
              الحفظ في أقصى اليسار. وصار أيقونةَ قرصِ الحفظ المعروفة بدل
              الجملة — واسمه يبقى في `title` و`aria-label` لمن يقرأ بالصوت
              أو يقف عليه، فلا يضيع المعنى بضياع النصّ. */}
          <button
            className={showProfit ? "btn-primary" : "btn-ghost"}
            title="تصفية ربح" aria-label="تصفية ربح"
            onClick={() => setShowProfit(s => !s)}
          >
            <Coins size={15} />
          </button>
          {isOwner && (
            <button className={hasUnsaved ? "btn-primary" : "btn-ghost"}
              title="حفظ الأوزان" aria-label="حفظ الأوزان"
              onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              <Save size={15} />
            </button>
          )}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full hidden lg:table">
          <thead><tr className="border-b border-[var(--hairline)]">
            <th className="th text-start">الشركة</th>
            <th className="th text-start">القيمة</th>
            <th className="th text-start">الوزن الحالي</th>
            <th className="th text-start">الوزن المستهدف %</th>
            {/* ثلاثة أعمدة لا أربعة: «عدد الأسهم» الكلي كان مجموع العمودين
                التاليين حرفياً — عمودٌ يُعيد قول ما بعده فيزحم الجدول بلا خبر.
                والأسهم هي وحدة القرار هنا (كم سهماً أشتري من كل مصدر)، فالمبلغ
                يبقى تحتها سطراً خافتاً لا عموداً مستقلاً. */}
            <th className="th text-start">المبلغ الكلي</th>
            <th className="th text-start">أسهم من السيولة</th>
            <th className="th text-start">أسهم من إعادة الاستثمار</th>
          </tr></thead>
          <tbody>
            {items.map((it: any) => {
              const { tw, liquidityShare, reinvestShare, totalAmount, totalShares, side, excessPct } = shareOf(it);
              return (
              <tr key={it.company_id}>
                {/* ══ الشعارُ والهلالُ في هويّة الصفّ ══ (بأمر المالك · D232)
                    الجدولُ أمرُ تنفيذٍ («اشترِ كذا سهماً»)، فالتعرّفُ على
                    الورقة بالشعار أسرعُ من قراءة الاسم، والحكمُ الشرعيُّ
                    شرطُ الأمر لا حاشيةٌ بجانبه. والهلالُ وحدَه يكفي —
                    بلونه وتلميحه — كما في صفحة السهم. */}
                <td className="td text-start">
                  <button type="button" onClick={() => setSheet(it.symbol)}
                    className="text-start hover:underline flex items-center gap-2 min-w-0"
                    title={`اعرض ورقة ${it.name}`}>
                    <CompanyLogo symbol={it.symbol} size={22} />
                    <span className="min-w-0">
                      <span className="text-[var(--ink)] font-semibold text-[13px]">{it.name}</span>
                      <span className="tag-b ms-1" style={{fontSize:10,padding:"2px 6px"}}>{it.symbol}</span>
                    </span>
                    <ShariaBadge status={it.sharia_status} size={13} />
                  </button>
                </td>
                <td className="td text-start text-[var(--ink)]">{fmt(it.market_value)}</td>
                <td className="td text-start"><span className="tag-n">{it.current_weight}%</span></td>
                <td className="td text-start">
                  {/* type=text + inputMode=decimal: يعرض الأرقام لاتينية بلا تشكيل
                      هندي يفرضه type=number على أجهزة اللغة العربية. أي رقم هندي
                      يُكتب يُحوَّل فورًا إلى لاتيني (٠-٩ و ۰-۹). */}
                  <input className="input" style={{width: 90, padding: "6px 10px"}} type="text" inputMode="decimal" lang="en"
                    value={val(it.company_id, it.target_weight)}
                    onChange={e => setTargets(s => ({ ...s, [it.company_id]:
                      e.target.value
                        .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660))
                        .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x06F0))
                        .replace(/[^\d.]/g, "") }))} />
                </td>
                <td className="td text-start">
                  {/* ══ الفائضُ يُعرض سالباً بلفظه ══ (D217)
                      رقمٌ سالبٌ وحدَه يُقرأ خطأً حسابياً؛ ومعه كلمةُ «بيع»
                      ولونُ النقصان يصير أمراً مفهوماً. ونقاطُ التجاوز في
                      التلميح: المبلغُ يقول كم، والنسبةُ تقول لماذا. */}
                  {tw <= 0
                    ? <span className="text-[var(--ink-muted)] text-xs">لم تحدد</span>
                    : side === "sell"
                      ? <span className="text-[var(--neg-ink)] text-xs font-bold tabular-nums" dir="ltr"
                          title={`الوزن الحالي يتجاوز المستهدف بـ${excessPct.toFixed(1)} نقطة`}>
                          {fmt(totalAmount)} <span className="font-normal">بيع</span>
                        </span>
                      : totalAmount == null
                        ? <span className="text-[var(--ink-muted)] text-xs" title="الفائض دون سعر سهم واحد">متوازنة</span>
                        : <span className="text-[var(--ink)] text-xs font-bold tabular-nums" dir="ltr">{fmt(totalAmount)}</span>}
                </td>
                <td className="td text-start">
                  {tw > 0
                    ? <div>
                        <span className="text-[var(--pos-ink)] text-xs font-bold tabular-nums" dir="ltr">
                          {shrOf(liquidityShare, it).toLocaleString("en-US")}
                        </span>
                      </div>
                    : <span className="text-[var(--ink-muted)] text-xs">لم تحدد</span>}
                </td>
                <td className="td text-start">
                  {tw > 0
                    ? <div>
                        <span className="text-[var(--brand-ink)] text-xs font-bold tabular-nums" dir="ltr">
                          {shrOf(reinvestShare, it).toLocaleString("en-US")}
                        </span>
                      </div>
                    : <span className="text-[var(--ink-muted)] text-xs">لم تحدد</span>}
                </td>
              </tr>
            );})}
          </tbody>
          {totals.amount > 0 && (
            <tfoot>
              <tr style={{borderTop:"2px solid var(--hairline)"}}>
                <td className="td text-start text-[var(--ink-muted)] text-xs font-semibold">المجموع</td>
                {/* تحت «القيمة»: مجموعُ قيمة المراكز — أساسُ الدخل المحسوب بجانبه. */}
                <td className="td text-start">
                  <span className="text-[var(--ink)] text-xs font-bold tabular-nums" dir="ltr">
                    {fmt(items.reduce((s: number, it: any) => s + (Number(it.market_value) || 0), 0))}
                  </span>
                </td>
                {/* تحت «الوزن الحالي»: دخلُ التوزيعات بأوزانك اليوم. */}
                <td className="td text-start">
                  {income.now > 0 ? (
                    <div className="leading-tight"
                         title={"دخلُ توزيعاتٍ سنويٌّ متوقَّع بأسعار اليوم"
                                + (income.unknown ? ` — ${income.unknown} شركة بلا عائد معلوم، خارج الحساب` : "")}>
                      <div className="text-[9px] text-[var(--ink-muted)]">توزيعات الآن</div>
                      <span className="text-[var(--pos-ink)] text-xs font-bold tabular-nums" dir="ltr">
                        {fmt(Math.round(income.now))}
                      </span>
                    </div>
                  ) : <span className="text-[var(--ink-muted)] text-xs">غير متوفّر</span>}
                </td>
                {/* تحت «الوزن المستهدف»: معدّلُ العائد بهذه الأوزان، ودخلُها بعد التوظيف. */}
                <td className="td text-start">
                  {dyWeighted != null ? (
                    <div className="leading-tight"
                         title={"معدّل عائد التوزيعات مرجّحاً بالوزن المستهدف، ودخلُه بعد توظيف النقد"
                                 + (dyAgg.unknown ? ` — ${dyAgg.unknown} شركة بلا عائد معلوم` : "")}>
                      <div className="text-[9px] text-[var(--ink-muted)]">
                        عند الهدف · {dyWeighted.toFixed(2)}%
                      </div>
                      <span className="text-[var(--pos-ink)] text-xs font-bold tabular-nums" dir="ltr">
                        {fmt(Math.round(income.after))}
                      </span>
                    </div>
                  ) : (
                    <span className="text-[var(--ink-muted)] text-xs">غير متوفّر</span>
                  )}
                </td>
                <td className="td text-start">
                  <span className="text-[var(--ink)] text-xs font-bold tabular-nums" dir="ltr">{fmt(totals.amount)}</span>
                </td>
                <td className="td text-start">
                  <span className="text-[var(--pos-ink)] text-xs font-bold tabular-nums" dir="ltr">
                    {totals.liqShares.toLocaleString("en-US")}
                  </span>
                </td>
                <td className="td text-start">
                  <span className="text-[var(--brand-ink)] text-xs font-bold tabular-nums" dir="ltr">
                    {totals.reiShares.toLocaleString("en-US")}
                  </span>
                </td>
              </tr>
            </tfoot>
          )}
        </table>

        {/* Mobile: بطاقة مباشرة لكل شركة — لا جدولاً مضغوطاً. رأسٌ (الاسم +
            حقل الوزن)، ثم المبلغ الكلي مقابل عدد الأسهم، ثم انقسامه إلى
            سيولة (أخضر) وإعادة استثمار (أزرق). لا حشو غير هذا. */}
        <div className="lg:hidden divide-y" style={{ borderColor: "var(--hairline)" }}>
          {items.map((it: any) => {
            const { tw, liquidityShare, reinvestShare, totalAmount, totalShares, side } = shareOf(it);
            return (
              <div key={it.company_id} className="py-3.5 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  {/* والبطاقةُ على الجوّال كالصفّ — لا شاشتان بحظّين. */}
                  <button type="button" onClick={() => setSheet(it.symbol)}
                    className="min-w-0 text-start flex items-center gap-2" title={`اعرض ورقة ${it.name}`}>
                    <CompanyLogo symbol={it.symbol} size={22} />
                    <span className="min-w-0">
                      <span className="text-[var(--ink)] font-semibold text-[13px]">{it.name}</span>{" "}
                      <span className="tag-b" style={{fontSize:10,padding:"2px 6px"}}>{it.symbol}</span>
                    </span>
                    <ShariaBadge status={it.sharia_status} size={13} />
                  </button>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {/* نسبةُ الامتلاك الحالية كعمود «الوزن الحالي» في جدول الحاسوب (D478) */}
                    <span className="tag-n tabular-nums" dir="ltr" title="نسبة الامتلاك الحالية">{it.current_weight}%</span>
                    <label className="text-[11px] text-[var(--ink-muted)]">الهدف %</label>
                    <input className="input" style={{width: 76, padding: "6px 10px"}} type="text" inputMode="decimal" lang="en"
                      value={val(it.company_id, it.target_weight)}
                      onChange={e => setTargets(s => ({ ...s, [it.company_id]:
                        e.target.value
                          .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660))
                          .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x06F0))
                          .replace(/[^\d.]/g, "") }))} />
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] text-[var(--ink-muted)]">
                      {side === "sell" ? "فائضٌ عن الوزن · بيع" : "المبلغ الكلي"}
                    </p>
                    <p className="text-sm font-bold tabular-nums" dir="ltr"
                      style={{ color: side === "sell" ? "var(--neg-ink)" : "var(--ink)" }}>
                      {tw <= 0 ? "لم تحدد"
                       : totalAmount == null ? "متوازنة"
                       : fmt(totalAmount)}
                    </p>
                  </div>
                  <div className="text-end">
                    <p className="text-[10px] text-[var(--ink-muted)]">عدد الأسهم</p>
                    <p className="text-sm font-bold text-[var(--ink)] tabular-nums" dir="ltr">
                      {tw > 0 && totalShares != null ? totalShares.toLocaleString("en-US", { maximumFractionDigits: 1 }) : "لم تحدد"}
                    </p>
                  </div>
                </div>
                {/* التقسيم بالأسهم لا بالريال: المبلغ الكلي أعلاه يكفي لمعرفة
                    الحجم، والقرار هنا «كم سهماً أشتري من كل مصدر» — والمبلغ
                    يحتاج قسمةً ذهنية على السعر قبل أن يصير أمراً منفَّذاً. */}
                <div className="pt-2 border-t border-[var(--hairline)] space-y-1.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-[var(--ink-muted)]">سيولة</span>
                    <span className="text-xs font-bold text-[var(--pos-ink)] tabular-nums" dir="ltr">
                      {tw > 0 ? shrOf(liquidityShare, it).toLocaleString("en-US") + " سهم" : "لم تحدد"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-[var(--ink-muted)]">إعادة استثمار</span>
                    <span className="text-xs font-bold text-[var(--brand-ink)] tabular-nums" dir="ltr">
                      {tw > 0 ? shrOf(reinvestShare, it).toLocaleString("en-US") + " سهم" : "لم تحدد"}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
          {/* صفُّ المجموع في الجوّال: ما يقوله tfoot في الحاسوب بعينه. */}
          {totals.amount > 0 && (
            <div className="py-3 flex items-center justify-between gap-3">
              <span className="text-[var(--ink-muted)] text-xs font-semibold">المجموع</span>
              <div className="flex items-center gap-4">
                <span className="text-[11px] text-[var(--ink-muted)]">عائد التوزيعات</span>
                {dyWeighted != null ? (
                  <span className="text-[var(--pos-ink)] text-xs font-bold tabular-nums" dir="ltr">
                    {dyWeighted.toFixed(2)}%
                  </span>
                ) : (
                  <span className="text-[var(--ink-muted)] text-xs">غير متوفّر</span>
                )}
                <span className="text-[var(--ink)] text-xs font-bold tabular-nums" dir="ltr">{fmt(totals.amount)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}

      {/* صورةُ التوزيع — تتحرّك مع الحقول قبل الحفظ (D191). */}
      <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--hairline)" }}>
        <AllocationCharts
          rows={items}
          currentOf={(r: any) => Number(r.current_weight) || 0}
          targetOf={(r: any) => Number(val(r.company_id, r.target_weight)) || 0} />
      </div>

      {showProfit && (
        <div className="mt-4 rounded-xl p-4" style={{background:"transparent", border: "1px solid var(--hairline)"}}>
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <p className="text-[var(--warn-ink)] text-xs font-bold">تصفية ربح</p>
            {/* العتبة هي القاعدة كلّها: مركزٌ بلغ ربحه العتبة قابلٌ للتصفية،
                وما دونها لا. رقمٌ واحد يحكم التصفية الأولى والثانية والعاشرة. */}
            <div className="flex items-center gap-1.5 rounded-lg ps-2.5 pe-1 py-1"
              style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
              <span className="text-[11px] text-[var(--warn-ink)] whitespace-nowrap">العتبة %</span>
              <NumInput className="text-[13px] font-bold tabular-nums bg-transparent border-0 outline-none text-[var(--ink)] p-0"
                style={{ width: 46, textAlign: "start" }}
                value={thrDraft}
                onChange={(v: string) => setThrDraft(v)} />
              {Number(thrDraft) !== (profitData?.threshold_pct ?? 20) && (
                <button className="btn-ghost" style={{ padding: "2px 6px", fontSize: 11 }}
                  onClick={() => saveThreshold.mutate(Number(thrDraft) || 0)}
                  disabled={saveThreshold.isPending}>حفظ</button>
              )}
            </div>
            {profitData && (
              <span className="mr-auto text-[11px] text-[var(--ink-muted)]">
                قابل للتصفية الآن: <span className="font-bold text-[var(--warn-ink)]">{profitData.eligible_count ?? 0}</span>
              </span>
            )}
          </div>
          {/* المحصّلة أولاً: لو نُفِّذ المقترح كاملاً، كم يدخل حسابك وكم منه ربح
              فعلاً. هذا التمييز هو ما يجعل «العائد المحقّق» في لوحة التحكم
              مفهوماً بدل أن يبدو أصغر مما تتوقّعه بعد كل تصفية. */}
          {profitData?.totals && profitData.rows?.length > 0 && (
            <div className="grid grid-cols-3 gap-2 mb-3">
              {([["حصيلة البيع", profitData.totals.proceeds, "text-[var(--ink)]"],
                 ["ربح محقّق",   profitData.totals.realized_if_sold, "profit"],
                 ["رأس مال عائد", profitData.totals.capital_returned, "text-[var(--ink-muted)]"]] as [string,number,string][]).map(([lbl, v, col]) => (
                <div key={lbl} className="rounded-xl px-3 py-2" style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
                  <div className="text-[10px] text-[var(--ink-muted)] whitespace-nowrap">{lbl}</div>
                  <div className={"text-base font-extrabold tabular-nums " + col} dir="ltr">{fmt(v)}</div>
                </div>
              ))}
            </div>
          )}
          {profitError ? (
            /* بلا هذه الحالة يبقى «جارٍ التحميل» معلّقاً إلى الأبد عند أي
               فشل، فيبدو التطبيق عالقاً بلا سبب ظاهر ولا سبيل لإعادة المحاولة. */
            <div className="flex items-center gap-2">
              <p className="text-[var(--neg-ink)] text-xs">تعذّر حساب التصفية.</p>
              <button className="btn-ghost text-[11px]" onClick={() => refetchProfit()}>إعادة المحاولة</button>
            </div>
          ) : !profitData ? (
            <p className="text-[var(--ink-muted)] text-xs">{profitLoading ? "جارٍ الحساب…" : "—"}</p>
          ) : profitData.rows.length === 0 ? (
            <p className="text-[var(--ink-muted)] text-xs">لا مراكز</p>
          ) : (
            /* بطاقة لكل شركة بهرمية صريحة بدل صفٍّ أفقي يحشر ستة حقول
               متساوية الحجم: الرقم المطلوب هنا واحد — كم سهماً أبيع لأقبض
               الربح وحده — فيتصدّر البطاقة، ويليه حجم الربح، وتُنزَل بيانات
               السعر إلى شبكة سفلية مصطفّة الأعمدة بين كل البطاقات فتُقارَن
               الشركات بالنظر رأسياً لا بقراءة كل سطر على حدة. */
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
              {profitData.rows.map((r: any) => (
                <div key={r.company_id} className="rounded-xl p-3"
                  style={{ background: "var(--panel)", border: "1px solid var(--hairline)" }}>
                  <div className="flex items-center gap-2 mb-2.5 min-w-0 flex-wrap">
                    <span className="text-[var(--ink)] font-bold text-[13px] truncate">{r.name}</span>
                    <span className="tag-b shrink-0" style={{fontSize:10,padding:"2px 6px"}}>{r.symbol}</span>
                    {/* الحكم صريحٌ على كل مركز — لا يُخفى غير القابل، فمعرفة
                        «كم ينقصه» جزءٌ من القرار كمعرفة أنه بلغ. */}
                    <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded" style={r.eligible
                      ? { background: "transparent", color: "var(--pos-ink)", border: "1px solid var(--hairline)" }
                      : { background: "transparent", color: "var(--ink-muted)", border: "1px solid var(--line)" }}>
                      {r.eligible ? "قابل للتصفية" : `دون العتبة · يلزمه ${(r.price_needed ?? 0).toFixed(2)}`}
                    </span>
                    {(r.prior_liquidations ?? 0) > 0 && (
                      <span className="shrink-0 text-[10px] text-[var(--ink-muted)]">صُفّي {r.prior_liquidations}×</span>
                    )}
                    {/* عتبة هذه الشركة — فارغةٌ تعني وراثة العتبة العامة. */}
                    <span className="mr-auto shrink-0 flex items-center gap-1">
                      <span className="text-[10px] text-[var(--ink-muted)]">عتبتها %</span>
                      <NumInput className="input tabular-nums"
                        style={{ width: 52, padding: "2px 6px", fontSize: 11 }}
                        value={thrRow[r.company_id] ?? String(r.threshold_pct ?? "")}
                        onChange={(v: string) => setThrRow(d => ({ ...d, [r.company_id]: v }))}
                        onBlur={() => {
                          const raw = thrRow[r.company_id];
                          setThrRow(d => { const n = { ...d }; delete n[r.company_id]; return n; });
                          if (raw == null) return;
                          const n = Number(raw);
                          if (raw !== "" && !Number.isNaN(n) && n !== r.threshold_pct)
                            saveCompanyThr.mutate({ id: r.company_id, pct: n });
                        }} />
                      {r.threshold_is_custom && (
                        <button className="btn-ghost" style={{ padding: "2px 4px" }} title="العتبة العامة"
                          onClick={() => {
                            setThrRow(d => { const n = { ...d }; delete n[r.company_id]; return n; });
                            saveCompanyThr.mutate({ id: r.company_id, pct: null });
                          }}>
                          <RefreshCw size={11} />
                        </button>
                      )}
                    </span>
                  </div>

                  <div className="flex items-end justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[10px] text-[var(--ink-muted)]">المتاح للتصفية</p>
                      <p className="text-lg font-extrabold tabular-nums leading-tight" dir="ltr"
                        style={{ color: r.eligible ? "var(--warn-ink)" : "var(--ink-muted)" }}>
                        {(r.eligible ? r.sellable_shares : 0).toLocaleString("en-US", {maximumFractionDigits:2})}
                      </p>
                      <p className="text-[10px] text-[var(--ink-muted)] tabular-nums" dir="ltr">
                        {r.shares_held.toLocaleString("en-US")} سهم مملوك
                      </p>
                    </div>
                    {/* العدّاد يتصدّر: هو الرقم القابل للحصاد الآن. والربح منذ
                        التأسيس تحته للسياق — سبق حصاد جزءٍ منه. */}
                    <div className="text-end shrink-0">
                      <p className="text-[10px] text-[var(--ink-muted)]">
                        {r.reference_is_last_sale ? "منذ آخر تصفية" : "ربح ورقي غير محقّق"}
                      </p>
                      <p className="text-lg font-extrabold tabular-nums leading-tight" dir="ltr"
                        style={{ color: (r.since_profit ?? 0) > 0 ? "var(--pos-ink)" : "var(--ink-muted)" }}>
                        {fmt(r.since_profit ?? 0)}
                      </p>
                      <p className="text-[10px] tabular-nums" dir="ltr"
                        style={{ color: (r.since_pct ?? 0) > 0 ? "var(--pos-ink)" : "var(--ink-muted)" }}>
                        {(r.since_pct ?? 0).toFixed(2)}%
                      </p>
                      {r.reference_is_last_sale && (
                        <p className="text-[10px] text-[var(--ink-muted)] tabular-nums mt-0.5" dir="ltr">
                          {fmt(r.unrealized_profit)} منذ التأسيس
                        </p>
                      )}
                    </div>
                  </div>

                  {/* تفصيل حصيلة البيع — هذا هو الجزء الذي كان غائباً تماماً:
                      حصيلة بيع هذه الأسهم تساوي الربح الورقي بحكم تعريف الكمية،
                      لكنها ليست ربحاً كلها؛ معظمها رأس مالك يعود إليك. إظهار
                      الشقّين صريحاً يمنع قراءة الحصيلة كأنها ربح محقّق. */}
                  <div className="mt-2.5 pt-2.5 border-t border-[var(--hairline)]">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-[10px] text-[var(--ink-muted)]">حصيلة البيع نقداً</span>
                      <span className="text-xs font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(r.proceeds ?? 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-[10px] text-[var(--ink-muted)]">منها ربح محقّق</span>
                      <span className="text-xs font-bold profit tabular-nums" dir="ltr">{fmt(r.realized_if_sold ?? 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] text-[var(--ink-muted)]">ومنها رأس مال عائد</span>
                      <span className="text-xs font-bold text-[var(--ink-muted)] tabular-nums" dir="ltr">{fmt(r.capital_returned ?? 0)}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2.5 border-t border-[var(--hairline)]">
                    {([[r.reference_is_last_sale ? "سعر آخر تصفية" : "متوسط التكلفة",
                        (r.reference_price ?? 0).toFixed(2)],
                       ["آخر إغلاق",     (r.last_price ?? 0).toFixed(2)],
                       ["الربح للسهم",   (r.profit_per_share ?? 0).toFixed(2)]] as [string,string][]).map(([lbl, v], i) => (
                      <div key={lbl}>
                        <p className="text-[10px] text-[var(--ink-muted)] whitespace-nowrap">{lbl}</p>
                        <p className={"text-xs font-bold tabular-nums " + (i === 2 ? "profit" : "text-[var(--ink)]")} dir="ltr">{v}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────
export default function PortfolioPage() {
  const t = useT();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  // بطاقة الشركة تُفتح فوق قسم المحفظة نفسه — لا انتقال لقسم السوق.
  const [sheetSymbol, setSheetSymbol] = useState<string | null>(null);
  const [searchFocused, setSearchFocused] = useState(false);
  const [addOpen, setAddOpen]   = useState(false);
  const [editComp, setEditComp] = useState<any>(null);
  const [txComp, setTxComp]     = useState<any>(null);
  const [delComp, setDelComp]   = useState<any>(null);
  const [editHold, setEditHold] = useState<any>(null);
  const [cashOpen, setCashOpen] = useState(false);
  const [colsOpen, setColsOpen] = useState(false);
  const [tab, setTab] = useState<"holdings" | "dashboard" | "watchlist" | "portfolioNews" | "portfolioCalendar" | "notifications">("holdings");
  const [dashSubTab, setDashSubTab] = useState<"grid" | "rebalance" | "liquidity">("grid");
  const { portfolioCols: cols, togglePortfolioCol } = useAppStore();
  const { isOwner } = useAuthStore();

  const { data: holdings = [], isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => holdingsApi.list().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });

  const { data: closed = [] } = useQuery({
    queryKey: ["holdings-closed"],
    queryFn: () => holdingsApi.closed().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });

  const { data: companies = [] } = useQuery({
    queryKey: ["companies"],
    queryFn: () => companiesApi.list().then(r => Array.isArray(r.data.data) ? r.data.data : []),
  });

  /* تحريك شركة في الترتيب. التحديث فوريّ في الذاكرة ثم يُحفظ — انتظار الشبكة
     بعد كل ضغطة يجعل السهم يبدو معطّلاً. والترتيب يُحسب على القائمة الكاملة لا
     المرشَّحة: التحريك داخل نتيجة بحثٍ يُنتج ترتيباً لا يفهمه المالك. */
  const reorder = useMutation({
    mutationFn: (order: number[]) => holdingsApi.setOrder(order).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
  const move = (companyId: number, dir: -1 | 1) => {
    const ids = holdings.map((x: any) => x.company_id ?? x.company?.id);
    const i = ids.indexOf(companyId);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= ids.length) return;
    const next = [...holdings];
    [next[i], next[j]] = [next[j], next[i]];
    qc.setQueryData(["portfolio"], next);
    reorder.mutate(next.map((x: any) => x.company_id ?? x.company?.id));
  };

  /* ترتيب بالضغطة المطوّلة: تضغط على الصفّ نصف ثانية فيصير قابلاً للسحب.

     ولماذا هذه لا سهمان: الصفّ كلّه هو المقبض، فلا هدف صغير يُصاب بالإصبع على
     الجوال، ولا عنصر إضافي يزحم الصفّ على الكمبيوتر. والمهلة تمنع أن يُفهم
     النقر العادي (لفتح صفحة الشركة) على أنه بداية سحب.

     والتنفيذ بمؤشّرات الإدخال (pointer events) لا بسحب HTML5: الأخير لا يعمل
     باللمس أصلاً، فكان الترتيب سيتعطّل على الجوال وحده بلا أثرٍ ظاهر. */
  const [dragId, setDragId] = useState<number | null>(null);
  const armTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragRef = useRef<number | null>(null);
  const startPt = useRef<{ x: number; y: number } | null>(null);
  const edgeY = useRef<number>(0);
  const scroller = useRef<number | null>(null);
  useEffect(() => () => { if (armTimer.current) clearTimeout(armTimer.current); }, []);

  /* منع تمرير الصفحة أثناء السحب باللمس.
     السبب: touch-action وحدها لا تكفي — المتصفّح يقرّر ملكية الإيماءة عند أول
     حركة، وتغييرُ الخاصية بعد التأشير يأتي متأخّراً، فيبدأ التمرير ويصل
     pointercancel فيسقط السحب. والمنع الصريح لحدث اللمس (بمستمعٍ غير سالب)
     هو الطريق الوحيد الموثوق. */
  useEffect(() => {
    if (dragId == null) return;
    const stop = (e: TouchEvent) => e.preventDefault();
    window.addEventListener("touchmove", stop, { passive: false });
    return () => window.removeEventListener("touchmove", stop);
  }, [dragId]);

  /* تمرير تلقائي عند حافّتي الشاشة أثناء السحب.
     بدونه لا يمكن نقل شركةٍ إلى موضعٍ خارج الشاشة أصلاً: البطاقة على الجوّال
     نحو ١٧٠ بكسل، فلا يظهر منها إلا أربع، والصفحة لا تتمرّر لأن اللمس مُعطَّل
     أثناء السحب — فتقف الحركة عند الحافّة بلا سببٍ مفهوم. */
  useEffect(() => {
    if (dragId == null) {
      if (scroller.current) { cancelAnimationFrame(scroller.current); scroller.current = null; }
      return;
    }
    /* الحاوية المتمرِّرة هي عنصرٌ داخلي (app-main) لا النافذة — فالنافذة لا
       تتمرّر في هذا التطبيق أصلاً، وscrollBy عليها بلا أثر. */
    const box = (document.querySelector("[data-cid]")?.closest(".overflow-y-auto")
                 || document.scrollingElement) as HTMLElement | null;
    const step = () => {
      const r = box?.getBoundingClientRect();
      const top = r ? r.top : 0, bottom = r ? r.bottom : window.innerHeight;
      const y = edgeY.current, m = 70;
      if (y > 0 && y - top < m) box?.scrollBy(0, -Math.ceil((m - (y - top)) / 5));
      else if (y > 0 && bottom - y < m) box?.scrollBy(0, Math.ceil((m - (bottom - y)) / 5));
      scroller.current = requestAnimationFrame(step);
    };
    scroller.current = requestAnimationFrame(step);
    return () => { if (scroller.current) cancelAnimationFrame(scroller.current); scroller.current = null; };
  }, [dragId]);

  const idsOf = (list: any[]) => list.map((x: any) => x.company_id ?? x.company?.id);

  const disarm = () => {
    if (armTimer.current) { clearTimeout(armTimer.current); armTimer.current = null; }
  };

  const dragProps = (cid: number) => ({
    "data-cid": cid,
    onPointerDown: (e: React.PointerEvent) => {
      // لا سحب أثناء البحث: الترتيب يُحسب على القائمة الكاملة، وتحريك صفٍّ داخل
      // نتيجةٍ مرشَّحة يقفز به مواضع لا يراها المالك.
      if (search) return;
      // الحقول والأزرار داخل الصفّ تبقى على وظيفتها.
      if ((e.target as HTMLElement).closest("input,select,textarea,button a")) return;
      disarm();
      startPt.current = { x: e.clientX, y: e.clientY };
      const el = e.currentTarget as HTMLElement;
      armTimer.current = setTimeout(() => {
        dragRef.current = cid;
        setDragId(cid);
        // أسرُ المؤشّر: تبقى أحداث الحركة قادمةً إلى هذا الصفّ حتى لو خرج
        // الإصبع عنه، وإلا انقطع السحب عند أوّل صفٍّ يُجتاز.
        try { el.setPointerCapture(e.pointerId); } catch { /* لا يدعمه كل متصفّح */ }
        if (navigator.vibrate) navigator.vibrate(12);
      }, 450);
    },
    onPointerMove: (e: React.PointerEvent) => {
      if (dragRef.current == null) {
        // اهتزاز الإصبع الطبيعي لا يُلغي الضغطة المطوّلة — تُلغى بحركةٍ قاصدة.
        const p0 = startPt.current;
        if (p0 && Math.hypot(e.clientX - p0.x, e.clientY - p0.y) > 10) disarm();
        return;
      }
      e.preventDefault();
      edgeY.current = e.clientY;
      const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
      const over = el?.closest("[data-cid]") as HTMLElement | null;
      const target = over ? Number(over.dataset.cid) : NaN;
      if (!target || target === dragRef.current) return;
      const cur = (qc.getQueryData(["portfolio"]) as any[]) || holdings;
      const ids = idsOf(cur);
      const i = ids.indexOf(dragRef.current), j = ids.indexOf(target);
      if (i < 0 || j < 0) return;
      const next = [...cur];
      next.splice(j, 0, next.splice(i, 1)[0]);
      qc.setQueryData(["portfolio"], next);
    },
    onPointerUp: () => {
      disarm();
      if (dragRef.current == null) return;
      const cur = (qc.getQueryData(["portfolio"]) as any[]) || holdings;
      reorder.mutate(idsOf(cur));
      dragRef.current = null;
      setDragId(null);
    },
    onPointerCancel: () => { disarm(); dragRef.current = null; setDragId(null); },
    // لا إلغاء عند مغادرة الصفّ: السحب طبيعته أن يجتاز الصفوف.
    style: dragId === cid
      ? { touchAction: "none" as const, cursor: "grabbing" as const,
          background: "transparent",
          boxShadow: "inset 0 0 0 1px rgba(56,189,248,.45)" }
      : { touchAction: dragId != null ? ("none" as const) : undefined },
  });

  /* حارس السلامة — صامتٌ في الخلفية. الفحوص تعمل كما كانت، لكن لا يُعرض منها
     شيء ما دامت سليمة: المعيار لا يُطلَب من المالك أن يضغط زرّه ولا أن يراه
     كل يوم. وحين ينكسر شيءٌ فعلاً — كإيداعٍ لم يُسجَّل يجعل الرصيد يخالف
     السجل — يظهر شريطٌ واحد يقول ماذا انكسر. */
  const { data: integrity } = useQuery({
    queryKey: ["portfolio-integrity"],
    queryFn: () => portfolioApi.integrity().then((r: any) => r.data.data),
    retry: 0,
    staleTime: 10 * 60 * 1000,
  });
  const broken = (integrity?.checks || []).filter((c: any) => c && c.ok === false);

  const filtered = holdings.filter((h: any) => {
    const q = search.toLowerCase();
    return !q || (h.company?.name || "").toLowerCase().includes(q)
              || (h.company?.name_ar || "").includes(q)
              || (h.company?.symbol || "").toLowerCase().includes(q);
  });

  // كل النتائج المطابقة لا أوّل ثمانٍ فقط: البحث عن «بنك» كان يعرض ثمانية
  // ويُخفي البقية بلا أي إشارة، فيبدو أن الشركة غير موجودة أصلاً. القائمة
  // نفسها قابلة للتمرير، فالطول لا يكسر التخطيط.
  const searchMatches = search.trim() ? searchCompanies(search, 400) : [];
  const goToSearchResult = (c: SaudiCompany) => {
    const held = holdings.find((h: any) => h.company?.symbol === c.symbol);
    setSearch("");
    setSearchFocused(false);
    // مملوكة → صفحتها داخل المحفظة. غير مملوكة → **بطاقة الشركة الكاملة** في
    // نافذة داخل قسم المحفظة نفسه: نظرة عامة وتقييم أداء وقوائم مالية وتوزيعات
    // ومفكرة ورأي الذكاء. كانت تفتح «تقييم الأداء» وحده، فتبدو الشركة منقوصة
    // لمجرّد أنك لا تملكها — والبيانات كلها متاحة أصلاً.
    if (held) navigate(`/portfolio/${held.company?.id}`);
    else setSheetSymbol(c.symbol);
  };

  if (isLoading) return (
    <div className="space-y-5 fade-in">
      <div className="h-8 skeleton w-48" />
      {[...Array(5)].map((_, i) => <div key={i} className="h-16 skeleton" />)}
    </div>
  );

  return (
    <div className="space-y-5 fade-in">
      {/* Header — ترحيب شخصي (كإيقاظ الأنظمة): صورة + تحية زمنية + الاسم،
          ومبدّل المحافظة على اليسار. */}
      <div className="flex items-center justify-between gap-3">
        <Greeting fallback={t("port.title")} />
        <PortfolioSwitcher />
      </div>


      <WealthW actions={
        <>
          {/* زرّان متساويان في الرتبة فيتساويان في الشكل: مربّعان ٣٦×٣٦
              بزاوية ١٢ (نصف زاوية الباند)، بحدٍّ من لون الهويّة وسطحٍ شفّاف.
              التمييز بالأيقونة لا بالشكل — وكانا زرّين بلغتين مختلفتين. */}
          <button className="wealth-act" onClick={() => setCashOpen(true)} title="السيولة" aria-label="السيولة">
            <Wallet size={17} />
          </button>
          {isOwner && (
            <button className="wealth-act" onClick={() => setAddOpen(true)} title={t("port.addCompany")} aria-label={t("port.addCompany")}>
              <Plus size={18} />
            </button>
          )}
        </>
      } />

      {/* Search — always visible (a stock lookup that stays in-page even
          when the company isn't held). */}
      <div className="relative">
        <Search size={15} className="absolute end-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" />
        <input
          className="input px-9"
          placeholder={t("port.searchCompany")}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setTimeout(() => setSearchFocused(false), 150)}
        />
        {searchFocused && search.trim() && searchMatches.length > 0 && (
          <div className="absolute top-full mt-1 start-0 end-0 z-30 rounded-xl overflow-hidden shadow-2xl"
            style={{background:"var(--pop)", border:"1px solid var(--line)", maxHeight: 300, overflowY: "auto"}}>
            {searchMatches.map(c => {
              const held = holdings.find((h: any) => h.company?.symbol === c.symbol);
              return (
                <button key={c.symbol}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 hover:bg-[var(--field)] text-start"
                  onMouseDown={() => goToSearchResult(c)}>
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="text-[var(--ink)] text-[13px] font-semibold truncate">{c.name_ar || c.name_en}</span>
                    {!held && <span className="text-[9.5px] text-[var(--ink-muted)] shrink-0">(غير مملوكة — عرض التحليل)</span>}
                  </span>
                  <span className="tag-b shrink-0" style={{fontSize:10}}>{c.symbol}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Tabs — under the search box. Mobile: centered icon-top strip.
          Desktop: icon + label side by side, each button stretching to fill
          the row evenly for a balanced, fuller look. */}
      <nav className="flex gap-2 justify-stretch pb-1" style={{ scrollbarWidth: "none" }}>
        {([
          ["holdings", "الحيازات", Briefcase],
          ["dashboard", "لوحة التحكم", LayoutGrid],
          ["watchlist", "المراقبة", Star],
          ["portfolioNews", "الأخبار", Newspaper],
          ["portfolioCalendar", "المفكرة", CalendarDays],
        ] as const).map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id}
            /* ══ أزرارٌ بلا إطار ══
               كانت تحمل `--field-line` وهو إطارُ الحقول: أسودُ ‎#2f2f2f في
               المظهر الفاتح. وهو صوابٌ لحقلٍ يُكتب فيه — الإطار يرسم حدود
               ما يُملأ — وثِقلٌ على زرٍّ لا يُملأ شيئاً. وخمسةُ أزرارٍ
               متجاورة بإطارٍ أسود تصنع شبكةً من الخطوط أثقل من محتواها.
               فالإطار يسقط، ويحمل التمييزَ ما هو أهدأ منه: أرضيةٌ مصبوغة
               للمفعَّل، وشفافيةٌ لغيره. */
            className="flex flex-col md:flex-row items-center justify-center gap-1 md:gap-2 flex-1 min-w-0 px-1.5 md:px-3 py-2 md:py-2.5 rounded-xl text-[10px] md:text-sm transition-colors"
            style={tab === id
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <Icon size={18} className="md:w-4 md:h-4 shrink-0" />
            <span className="whitespace-nowrap">{label}</span>
          </button>
        ))}
      </nav>

      {/* ثلاثة أزرارٍ في صفٍّ واحد بأعمدةٍ متساوية — من اليمين إلى اليسار،
          يملأ السطر تماماً بلا زائدٍ ولا ناقص. وكان `grid-cols-2` على الجوّال
          يترك الثالث وحده في سطرٍ ثانٍ بعرض النصف. */}
      {/* ══ تبويباتٌ فرعية بلغة التطبيق ══ (بأمر المالك)
          كانت وحدها تحمل أرضيةً للخامل (‏--surface) وإطاراً للمفعَّل —
          لغةٌ ثالثة بين أزرار التطبيق. وأزرارُ التطبيق أهدأ: أرضيةٌ
          مصبوغة بـ12٪ من لون الهوية للمفعَّل، وشفافيةٌ تامّة لغيره، بلا
          إطارٍ في الحالين. فوُحِّدت هذه معها حرفياً. */}
      {tab === "dashboard" && (
        <div className="grid grid-cols-3 gap-2">
          <button onClick={() => setDashSubTab("grid")}
            aria-pressed={dashSubTab === "grid"}
            className={"flex-1 min-w-0 flex items-center justify-center gap-1 px-1.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs whitespace-nowrap transition-colors "
              + (dashSubTab === "grid" ? "font-bold" : "text-[var(--ink-muted)] hover:text-[var(--ink)]")}
            style={dashSubTab === "grid"
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <LayoutGrid size={14} /> الرئيسي
          </button>
          <button onClick={() => setDashSubTab("rebalance")}
            aria-pressed={dashSubTab === "rebalance"}
            className={"flex-1 min-w-0 flex items-center justify-center gap-1 px-1.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs whitespace-nowrap transition-colors "
              + (dashSubTab === "rebalance" ? "font-bold" : "text-[var(--ink-muted)] hover:text-[var(--ink)]")}
            style={dashSubTab === "rebalance"
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <Scale size={14} /> التوزيع النسبي
          </button>
          <button onClick={() => setDashSubTab("liquidity")}
            aria-pressed={dashSubTab === "liquidity"}
            className={"flex-1 min-w-0 flex items-center justify-center gap-1 px-1.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs whitespace-nowrap transition-colors "
              + (dashSubTab === "liquidity" ? "font-bold" : "text-[var(--ink-muted)] hover:text-[var(--ink)]")}
            style={dashSubTab === "liquidity"
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <Droplets size={14} /> إدارة السيولة
          </button>
        </div>
      )}

      {/* Grid dashboard stays mounted (just hidden) even on other tabs/sub-tabs
          — its width-tracking ResizeObserver attaches to this node once on
          mount and never reattaches, so unmounting/remounting it on every
          switch left it frozen at a stale width until an actual window
          resize forced a re-measure. */}
      <div style={{ display: tab === "dashboard" && dashSubTab === "grid" ? undefined : "none" }}>
        <DashboardGrid />
      </div>
      {tab === "dashboard" && dashSubTab === "rebalance" && <RebalanceCard />}
      {tab === "dashboard" && dashSubTab === "liquidity" && <LiquidityTab />}
      {tab === "watchlist" && <WatchlistTab onOpen={(symbol) => setSheetSymbol(symbol)} />}
      {tab === "portfolioNews" && <PortfolioNewsPage />}
      {tab === "portfolioCalendar" && <PortfolioCalendarPage />}
      {tab === "notifications" && <NotificationsPage />}

      {tab !== "holdings" ? null : (
      <>
      {/* Table */}
      <div className="card overflow-x-auto p-0">
        {/* Column customization (point 10) */}
        <div className="flex items-center justify-end px-3 pt-2 relative">
          <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--ink)] hover:bg-[var(--field)] transition-all"
            title="تخصيص الأعمدة" onClick={() => setColsOpen(o => !o)}>
            <Columns3 size={15} />
          </button>
          {colsOpen && (
            <div className="absolute top-9 end-3 z-30 rounded-xl p-2 shadow-2xl"
              style={{background:"var(--pop)", border:"1px solid var(--line)", minWidth: 170}}>
              {([["sector", t("common.sector")], ["shares", t("port.shares")], ["avgCost", t("port.avgCost")],
                 ["lastPrice", "آخر سعر"], ["marketValue", t("port.marketValue")],
                 ["pnl", t("common.pnl")], ["dividends", "عائد التوزيعات"], ["actions", t("common.actions")]] as const).map(([id, label]) => (
                <button key={id} className="w-full flex items-center justify-between gap-3 px-2 py-1.5 rounded-lg hover:bg-[var(--field)] text-xs text-[var(--ink)]"
                  onClick={() => togglePortfolioCol(id)}>
                  {label}
                  {/* اللون بأسلوب صريح لا بصنف text-[var(--ink)]: القاعدة العامة
                      html.light .text-[var(--ink)] تقلبه إلى داكن فيظهر أسود على
                      الأزرق في المظهر الفاتح. */}
                  <span className="w-3.5 h-3.5 rounded flex items-center justify-center text-[9.5px] font-bold"
                    style={cols[id] ? { background: "var(--chart-1)", color: "#ffffff" } : { background: "var(--line)" }}>
                    {cols[id] ? "✓" : ""}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
        <table className="w-full hidden lg:table">
          <thead>
            <tr className="border-b border-[var(--hairline)]">
              <th className="th text-start">{t("common.company")}</th>
              {cols.sector && <th className="th text-start">{t("common.sector")}</th>}
              {cols.shares && <th className="th text-start">{t("port.shares")}</th>}
              {cols.avgCost && <th className="th text-start">{t("port.avgCost")}</th>}
              {cols.lastPrice && <th className="th text-start">آخر سعر</th>}
              {cols.marketValue && <th className="th text-start">{t("port.marketValue")}</th>}
              {cols.pnl && <th className="th text-start">{t("common.pnl")}</th>}
              {cols.dividends && <th className="th text-start">عائد التوزيعات</th>}
              {cols.actions && <th className="th text-start">{t("common.actions")}</th>}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={1 + Object.values(cols).filter(Boolean).length} className="td text-center text-[var(--ink-muted)] py-10">{t("port.empty")}</td></tr>
            )}
            {filtered.map((h: any) => {
              const pnl    = (h.current_value || 0) - (h.total_cost || 0);
              const pnlPct = h.total_cost ? (pnl / h.total_cost) * 100 : 0;
              const avgCost = h.total_shares ? (h.total_cost / h.total_shares) : 0;
              const divPct = h.total_cost ? (h.total_dividends_received || 0) / h.total_cost * 100 : 0;
              return (
                <tr key={h.id} className="hover:bg-[var(--field)] transition-colors group"
                  {...dragProps(h.company_id ?? h.company?.id)}>
                  <td className="td">
                    <button onClick={() => navigate("/portfolio/" + h.company?.id)} className="text-start hover:opacity-80 transition-opacity">
                      {(() => {
                        const dir = lookupCompany(h.company?.symbol);
                        const ar = dir?.name_ar || h.company?.name_ar || h.company?.name;
                        const en = dir?.name_en || (h.company?.name !== ar ? h.company?.name : "");
                        return (
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <CompanyLogo symbol={h.company?.symbol} color={h.company?.color} size={30} logoUrl={h.company?.logo_url} />
                            <ShariaBadge status={h.company?.sharia_status} />
                            <span className="text-[var(--ink)] font-bold text-[13px]">{ar}</span>
                            <span className="tag-b" style={{fontSize: 10, padding: "2px 7px"}}>{h.company?.symbol}</span>
                            {en && <span className="text-[var(--ink-muted)] text-[11px]" dir="ltr">{en}</span>}
                          </div>
                        );
                      })()}
                    </button>
                  </td>
                  {cols.sector && <td className="td">
                    <span className="tag-b">{h.company?.sector || "—"}</span>
                  </td>}
                  {cols.shares && <td className="td text-[var(--ink)]">{h.total_shares?.toLocaleString("en-US") ?? "—"}</td>}
                  {cols.avgCost && <td className="td text-[var(--ink)]">{fmt2(avgCost)}</td>}
                  {cols.lastPrice && <td className="td text-[var(--ink)]">
                    {/* آخرُ سعرٍ حيٌّ من المجرى، ورقمُ الاستعلام إن لم
                        يصل دفعٌ — مكوّنٌ واحدٌ لكلّ الشاشات (D330). */}
                    <LivePrice symbol={h.company?.symbol || h.symbol}
                               fallback={h.last_price} />
                  </td>}
                  {cols.marketValue && <td className="td text-[var(--ink)] font-semibold">
                    {/* وما يُبنى على السعر يتبعه: أسهمٌ × سعرٌ حيّ (D330) */}
                    <LiveValue symbol={h.company?.symbol || h.symbol}
                               shares={h.total_shares}
                               fallback={h.current_value} />
                  </td>}
                  {/* الربح/الخسارة: سطران بهرمية واضحة — المبلغ هو الرقم
                      الرئيسي، والنسبة تابعٌ أصغر تحته. حُذفت أيقونة الاتجاه
                      لأن السهم يقولها أصلاً، وأيقونةٌ فوق سهمٍ فوق إشارةِ +
                      ثلاثُ إشاراتٍ لمعنًى واحد. `tabular-nums` يجعل الأرقام
                      متساوية العرض فتصطفّ الصفوف عمودياً، و`dir=ltr` يثبّت
                      ترتيب السهم والإشارة فلا ينقلبان في RTL. */}
                  {cols.pnl && <td className="td">
                    <div className="leading-tight">
                      <p className={"text-sm font-semibold tabular-nums whitespace-nowrap " + (pnl >= 0 ? "profit" : "loss")}
                        dir="ltr">{pnl >= 0 ? "+" : ""}{fmt(pnl)}</p>
                      <p className={"text-[11px] tabular-nums whitespace-nowrap mt-0.5 flex items-center gap-1 " + (pnl >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}
                        dir="ltr">
                        {pnlPct.toFixed(2)}%
                        {pnl >= 0 ? <TrendingUp size={11} className="shrink-0" /> : <TrendingDown size={11} className="shrink-0" />}
                      </p>
                    </div>
                  </td>}
                  {cols.dividends && <td className="td">
                    {h.total_dividends_received > 0
                      ? <span className="tag-g">+{fmt(h.total_dividends_received)} · {divPct.toFixed(2)}%</span>
                      : <span className="text-[var(--ink-muted)] text-xs">—</span>}
                  </td>}
                  {cols.actions && <td className="td">
                    {!isOwner ? <span className="text-[var(--ink-muted)] text-xs">—</span> : <div className="flex items-center gap-1">
                      <button onClick={() => setTxComp(h.company)} title="شراء/بيع"
                        className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all">
                        <ShoppingCart size={14} />
                      </button>
                      <button onClick={() => setEditHold(h)} title="تعديل الأسهم/التكلفة"
                        className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all">
                        <SlidersHorizontal size={14} />
                      </button>
                      <button onClick={() => setEditComp(h.company)} title="تعديل"
                        className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => setDelComp(h.company)} title="حذف"
                        className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all">
                        <Trash2 size={14} />
                      </button>
                    </div>}
                  </td>}
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Mobile: one card per company instead of a cramped wide table */}
        <div className="lg:hidden divide-y" style={{ borderColor: "var(--hairline)" }}>
          {filtered.length === 0 && (
            <div className="text-center text-[var(--ink-muted)] py-10 text-sm">{t("port.empty")}</div>
          )}
          {filtered.map((h: any) => {
            const pnl    = (h.current_value || 0) - (h.total_cost || 0);
            const pnlPct = h.total_cost ? (pnl / h.total_cost) * 100 : 0;
            const avgCost = h.total_shares ? (h.total_cost / h.total_shares) : 0;
            const divPct = h.total_cost ? (h.total_dividends_received || 0) / h.total_cost * 100 : 0;
            const dir = lookupCompany(h.company?.symbol);
            const ar = dir?.name_ar || h.company?.name_ar || h.company?.name;

            /* بأمر المالك (D478): كلُّ شركةٍ في المحفظة ببطاقتها الكاملة كما في
               جدول الحاسوب — لا تُطوى في سطرِ «مركز مغلق». */

            return (
              <div key={h.id} className="p-3.5 space-y-3" {...dragProps(h.company_id ?? h.company?.id)}>
                <div className="flex items-center justify-between gap-2">
                  <button onClick={() => navigate("/portfolio/" + h.company?.id)} className="flex items-center gap-2 min-w-0 text-start">
                    <CompanyLogo symbol={h.company?.symbol} color={h.company?.color} size={32} logoUrl={h.company?.logo_url} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <ShariaBadge status={h.company?.sharia_status} />
                        <span className="text-[var(--ink)] font-bold text-[13px] truncate">{ar}</span>
                        <span className="tag-b" style={{fontSize: 10, padding: "2px 7px"}}>{h.company?.symbol}</span>
                      </div>
                      {cols.sector && h.company?.sector && <span className="text-[var(--ink-muted)] text-[11px]">{h.company.sector}</span>}
                    </div>
                  </button>
                </div>

                {/* شكلٌ واحد لكل الخانات: سطر التسمية فوق سطر الرقم، والرقم
                    بحجمه الطبيعي، والاثنان بمحاذاة اليمين — مكان بداية القراءة
                    في العربية. توحيد الشكل هو ما يجعل الشبكة تُقرأ عمودياً بلا
                    تفاوت، والتسمية في سطرها تتّسع كاملةً فلا يلتفّ رقمٌ ولا
                    تتمدّد البطاقة أفقياً: العرض من الشبكة لا من المحتوى. */}
                <div className="grid gap-x-1.5 gap-y-2 text-xs items-center"
                  style={{ gridTemplateColumns: "1fr auto 1fr" }}>
                  {cols.shares && (
                    <div className="min-w-0 text-right" style={{ gridColumn: 1, gridRow: 1 }}>
                      <span className="block text-[10px] text-[var(--ink-muted)] leading-tight whitespace-nowrap">عدد الأسهم :</span>
                      <span className="block whitespace-nowrap text-[var(--ink)] font-semibold tabular-nums">{h.total_shares?.toLocaleString("en-US") ?? "—"}</span>
                    </div>
                  )}
                  {/* **آخر سعر في القلب** — بين الأربعة، في إطارٍ قائم الزوايا
                      يفصله عنها بلا أن يُقلّدها: هو سؤال اللحظة، وهي حساب
                      الرحلة.
                      ويتلوّن بتغيّر اليوم عن إغلاق أمس لا بربحك الكلّي؛ وغياب
                      التغيّر يعني رماديّاً بلا لون — لا أخضرَ ثباتٍ مُختلَق. */}
                  {/* ══ «آخر سعر» على الجوال ══ (بأمر المالك)
                      كانت الكلمة **داخل** الإطار فتأكل ثلثه وتُكبّره بلا داعٍ،
                      وهي تسمية لا قيمة. فخرجت إلى الصفّ كسائر التسميات، وبقي
                      الإطار للرقم ونسبته وحدهما — أصغرَ وأكثفَ، وكلاهما ثقيل.
                      والتعادل أسودُ صريح: كان يُحسب مع الصعود (‏>= 0) فيظهر
                      أخضرَ وهو لم يتحرّك — لونُ ربحٍ لم يقع. */}
                  {cols.lastPrice && (() => {
                    const c = h.change_pct;
                    const flat = c != null && c === 0;
                    const ink = c == null || flat ? "var(--ink)"
                              : c > 0 ? "var(--pos-ink)" : "var(--neg-ink)";
                    // الخانة تشغل الصفّين، وكانت تُوسَّط بينهما فيطفو إطارها
                    // فوق سطر الأرقام السفلي. `self-stretch` مع `justify-end`
                    // يُنزلها حتى يستقرّ حدّها الأدنى على خطّ الصفّ الأسفل
                    // نفسه — لا فوقه ولا تحته.
                    return (
                    <div className="min-w-0 text-center shrink-0 self-stretch flex flex-col justify-between"
                      style={{ gridColumn: 2, gridRow: "1 / span 2" }}>
                      {/* التسمية بخطّ سائر التسميات ولونها ومقاسها حرفياً
                          (‏10px · ink-muted · leading-tight · «: » في آخرها)،
                          فلا تُقرأ خانةً من نوعٍ آخر.
                          وهي تعلو في صدر الخانة كتسميات جيرانها، لا ملتصقةً
                          بسقف المربّع: `justify-between` يدفعها إلى الأعلى
                          والمربّع إلى القاع. وقِيس أنّ العمود لا فضل فيه
                          (‏69 = 13 تسمية + 56 مربّعاً، فالفجوة صفر)، فأُضيف
                          فراغٌ صريح 8px بينهما: التسمية عنوانٌ للخانة لا
                          سقفٌ ملتصقٌ بها. */}
                      <span className="block text-[10px] text-[var(--ink-muted)] leading-tight whitespace-nowrap">آخر سعر :</span>
                      {/* عرضٌ ثابت لا يتبع عدد الخانات: كان `inline-block`
                          يتقلّص على محتواه، فيخرج إطار «8.07» أضيق من
                          «203.20» — أبعادٌ تختلف من شركةٍ إلى أخرى في عمودٍ
                          واحد، والعين تقرأ الاختلاف تفاوتاً في الأهمّية.
                          فثُبّت العرض على أوسع رقمٍ محتمل ويُوسَّط ما دونه. */}
                      <div className="leading-tight px-0.5 py-1 mx-auto mt-2 flex flex-col items-center justify-center"
                        style={{
                          width: 48, height: 48, borderRadius: 8,
                          border: "1px solid " + (c == null || flat ? "var(--hairline)"
                            : c > 0 ? "color-mix(in srgb, var(--pos-ink) 45%, transparent)"
                            : "color-mix(in srgb, var(--neg-ink) 45%, transparent)"),
                          background: c == null || flat ? "transparent"
                            : c > 0 ? "color-mix(in srgb, var(--pos-ink) 8%, transparent)"
                            : "color-mix(in srgb, var(--neg-ink) 8%, transparent)",
                        }}>
                        <LivePrice symbol={h.company?.symbol || h.symbol}
                          fallback={h.last_price}
                          className="hold-price-val block tabular-nums whitespace-nowrap"
                          style={{ margin: 0, color: ink }} />
                        {/* سطر النسبة **لا يغيب**. كان يُحذف حين يتعذّر قياس
                            تغيّر اليوم (‏`change_pct = null`: السهم لم يصل بعد
                            إلى مخزَّن الأسعار ولا إلى لقطة المحرّكين)، فينكمش
                            الإطار ويظهر صفٌّ بغير شكل جيرانه — وهو ليس تصميماً
                            بل قيمةٌ غائبة سُمح لها بأن تُغيّر البنية. الغياب
                            يُقال «—» في موضعه: البنية واحدة، والنقص مُعلَن. */}
                        <span className="hold-price-chg tabular-nums whitespace-nowrap flex items-center justify-center gap-0.5"
                          dir="ltr" style={{ color: c == null ? "var(--ink-muted)" : ink }}>
                          {c == null ? "—" : (c > 0 ? "+" : "") + c.toFixed(2) + "%"}
                          {c == null || flat ? null : c > 0 ? <TrendingUp size={8} className="shrink-0" /> : <TrendingDown size={8} className="shrink-0" />}
                        </span>
                      </div>
                    </div>
                    );
                  })()}
                  {/* العمودان الأيسران إلى أقصى اليسار: يُخلي ذلك القلبَ لآخر
                      سعر، ويجعل أرقام كل عمودٍ متحاذية رأسياً على حرفها. */}
                  {cols.avgCost && (
                    <div className="min-w-0 text-left" style={{ gridColumn: 3, gridRow: 1 }}>
                      {/* الكتلة تلتفّ على أطول سطرٍ فيها (التسمية) وتُدفع إلى
                          أقصى اليسار، والرقم بمحاذاة اليمين داخلها — فينتهي
                          الرقم عند طرف تسميته تماماً لا عند طرف الخانة. */}
                      <span className="inline-block text-right">
                        <span className="block text-[10px] text-[var(--ink-muted)] leading-tight whitespace-nowrap">{t("port.avgCost")} :</span>
                        <span className="block whitespace-nowrap text-[var(--ink)] font-semibold tabular-nums">{fmt2(avgCost)}</span>
                      </span>
                    </div>
                  )}
                  {cols.pnl && (
                    <div className="min-w-0 text-right" style={{ gridColumn: 1, gridRow: 2 }}>
                      <span className="block text-[10px] text-[var(--ink-muted)] leading-tight">الربح غير المحقّق :</span>
                      <span className={"hold-pnl block whitespace-nowrap font-semibold tabular-nums " + (pnl >= 0 ? "profit" : "loss")} dir="ltr">
                        {pnl >= 0 ? "+" : ""}{fmt(pnl)} · {pnlPct.toFixed(2)}%
                      </span>
                    </div>
                  )}
                  {cols.marketValue && (
                    <div className="min-w-0 text-left" style={{ gridColumn: 3, gridRow: 2 }}>
                      <span className="inline-block text-right">
                        <span className="block text-[10px] text-[var(--ink-muted)] leading-tight whitespace-nowrap">{t("port.marketValue")} :</span>
                        <FlashPrice value={h.current_value} style={{ margin: 0 }}
                          className="block whitespace-nowrap text-[var(--ink)] font-semibold tabular-nums">{fmt(h.current_value)}</FlashPrice>
                      </span>
                    </div>
                  )}
                  {cols.dividends && (
                    <div className="min-w-0 text-right" style={{ gridColumn: "1 / span 3", gridRow: 3 }}>
                      <span className="block text-[10px] text-[var(--ink-muted)] leading-tight">عائد التوزيعات :</span>
                      {h.total_dividends_received > 0
                        ? <span className="block whitespace-nowrap text-[var(--pos-ink)] font-semibold tabular-nums" dir="ltr">+{fmt(h.total_dividends_received)} · {divPct.toFixed(2)}%</span>
                        : <span className="block text-[var(--ink-muted)]">—</span>}
                    </div>
                  )}
                </div>

                {cols.actions && isOwner && (
                  <div className="flex items-center gap-1 pt-1 border-t border-[var(--hairline)]">
                    <button onClick={() => setTxComp(h.company)} title="شراء/بيع"
                      className="flex-1 p-2 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all flex items-center justify-center">
                      <ShoppingCart size={15} />
                    </button>
                    <button onClick={() => setEditHold(h)} title="تعديل الأسهم/التكلفة"
                      className="flex-1 p-2 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all flex items-center justify-center">
                      <SlidersHorizontal size={15} />
                    </button>
                    <button onClick={() => setEditComp(h.company)} title="تعديل"
                      className="flex-1 p-2 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all flex items-center justify-center">
                      <Pencil size={15} />
                    </button>
                    <button onClick={() => setDelComp(h.company)} title="حذف"
                      className="flex-1 p-2 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all flex items-center justify-center">
                      <Trash2 size={15} />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Charts — real allocation of the current portfolio */}
      <PortfolioCharts holdings={holdings} />

      {/* Portfolio-level financial indicators (weighted averages) */}
      <PortfolioMetricsCard />

      {/* الصفقات المغلقة (D480): ما بيع كاملاً يبقى بسجلّه وربحه المحقَّق
          ولو حُذف من الجدول — والشراء فيه من جديد يُكمل السجلّ نفسه. */}
      {closed.length > 0 && (
        <div className="card">
          <CollapsibleList label="الصفقات المغلقة" count={closed.length}>
            <div className="divide-y divide-[var(--hairline)]">
              {closed.map((c: any) => (
                <button key={c.company_id} onClick={() => navigate("/portfolio/" + c.company_id)}
                  className="w-full min-h-[40px] py-2 flex items-center gap-2.5 text-start hover:bg-[var(--field)] transition-colors">
                  <CompanyLogo symbol={c.symbol} size={24} />
                  <span className="text-[var(--ink)] font-semibold text-[13px]">{lookupCompany(c.symbol)?.name_ar || c.name}</span>
                  <span className="tag-b" style={{fontSize: 10, padding: "2px 7px"}}>{c.symbol}</span>
                  <span className="text-[var(--ink-muted)] text-[11px] tabular-nums" dir="ltr">
                    {(c.opened_at || "").slice(0, 10)} → {(c.closed_at || "").slice(0, 10)}
                  </span>
                  <span className="text-[var(--ink-muted)] text-[11px]">{c.transactions} عملية</span>
                  <span className={"ms-auto text-sm font-semibold tabular-nums " + (c.realized_gain >= 0 ? "profit" : "loss")}
                    dir="ltr">{c.realized_gain >= 0 ? "+" : ""}{fmt2(c.realized_gain)}</span>
                </button>
              ))}
            </div>
          </CollapsibleList>
        </div>
      )}

      {/* Companies without holdings — قائمة منسدلة */}
      {companies.length > 0 && (
        <div className="card">
          <CollapsibleList label={t("port.allCompanies")} count={companies.length}>
            <div className="flex flex-wrap gap-2">
              {companies.map((c: any) => (
                <button key={c.id} onClick={() => navigate("/portfolio/" + c.id)} title={c.name_ar || c.name}
                  className="tag-n hover:text-[var(--ink)] transition-colors cursor-pointer flex items-center gap-1.5">
                  <CompanyLogo symbol={c.symbol} size={18} logoUrl={c.logo_url} />
                  <span>{c.symbol}</span>
                </button>
              ))}
            </div>
          </CollapsibleList>
        </div>
      )}
      </>
      )}

      {/* شريط السلامة — لا يظهر إلا عند كسرٍ فعلي */}
      {broken.length > 0 && (
        <div className="rounded-xl p-3 flex items-start gap-2.5"
          style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
          <AlertTriangle size={15} className="text-[var(--neg-ink)] shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-[12.5px] font-bold text-[var(--neg-ink)]">
              {broken.length === 1 ? "فحص سلامة لم يمرّ" : `${broken.length} فحوص سلامة لم تمرّ`}
            </p>
            <p className="text-[11.5px] text-[var(--ink-muted)] mt-0.5">{broken[0].name}{broken[0].detail ? ` — ${broken[0].detail}` : ""}</p>
          </div>
        </div>
      )}

      {/* Modals */}
      {addOpen   && <CompanyModal onClose={() => setAddOpen(false)} />}
      {editComp  && <CompanyModal company={editComp} onClose={() => setEditComp(null)} />}
      {txComp    && <TransactionModal company={txComp} onClose={() => setTxComp(null)} />}
      {delComp   && <DeleteModal company={delComp} onClose={() => setDelComp(null)} />}
      {editHold  && <HoldingModal holding={editHold} onClose={() => setEditHold(null)} />}
      {cashOpen  && <CashModal onClose={() => setCashOpen(false)} />}
      {sheetSymbol && <StockSheet symbol={sheetSymbol} onClose={() => setSheetSymbol(null)} />}
    </div>
  );
}
