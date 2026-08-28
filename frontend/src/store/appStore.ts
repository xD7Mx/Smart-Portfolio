import { create } from "zustand";
import { persist } from "zustand/middleware";
import { settingsApi } from "../services/api";

// يحفظ التخطيط الكامل على الخادم (للمالك فقط؛ غير المالك يُرفض بهدوء بلا أثر)
// كي يتوحّد على كل الأجهزة: ترتيب القائمة + إخفاؤها + صفحة البداية + شبكة
// لوحة التحكم (الودجت) نفسها. لا ينتظر النتيجة حتى لا يُبطئ الواجهة.
let _pushTimer: ReturnType<typeof setTimeout> | null = null;
/* الحمولة تُكمَّل من الحالة الحيّة لا من نداء الاستدعاء: كان كل مُستدعٍ
   يعدّد الحقول بيده، فمن أضاف حقلاً جديداً (كأعمدة الجدول) وجب عليه تعديل
   ثمانية مواضع — ونسيانُ واحدٍ منها يعني إعداداً يُحفظ أحياناً ويُمحى
   أحياناً. الإكمال هنا مرّةً واحدة يمنع ذلك بنيوياً. */
function _pushLayout(payload: any) {
  if (_pushTimer) clearTimeout(_pushTimer);
  _pushTimer = setTimeout(() => {
    const s: any = useAppStore.getState();
    settingsApi.saveLayout({
      pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage,
      layouts: s.layouts, activeLayout: s.activeLayout, portfolioCols: s.portfolioCols,
      ...payload,
    }).catch(() => {});
  }, 500);
}

export interface GridItem { i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number }
export interface DashLayout { name: string; grid: GridItem[] }

/* ── Default workspace layout (user can edit/add/reset) ────── */
// "wealth"/"summary" don't sit here anymore — "لوحة التحكم" is now a tab
// inside صفحة المحفظة, which already shows the wealth band once, above the
// tab bar itself; keeping another copy of it in the grid just duplicated it.
const DEFAULT_GRID: GridItem[] = [
  // Top-3 gainers/losers, each its own card instead of one single-mover tile.
  // (تاسي/برنت أُزيلا من لوحة التحكم — يبقيان في شاشة السوق فقط.)
  { i: "gainer1",      x: 0, y: 0,  w: 4,  h: 1, minW: 3 },
  { i: "gainer2",      x: 4, y: 0,  w: 4,  h: 1, minW: 3 },
  { i: "gainer3",      x: 8, y: 0,  w: 4,  h: 1, minW: 3 },
  { i: "loser1",       x: 0, y: 1,  w: 4,  h: 1, minW: 3 },
  { i: "loser2",       x: 4, y: 1,  w: 4,  h: 1, minW: 3 },
  { i: "loser3",       x: 8, y: 1,  w: 4,  h: 1, minW: 3 },
  // نمو العائد + توزيع القطاعات جنبًا إلى جنب (يملأ القطاعُ الفراغَ بجانب العائد)،
  // ثم الأهداف، ثم أداء المحفظة بعدها.
  { i: "returngrowth", x: 0, y: 2,  w: 6,  h: 3, minW: 4, minH: 3 },
  { i: "sectors",      x: 6, y: 2,  w: 6,  h: 3, minW: 3, minH: 2 },
  { i: "goals",        x: 0, y: 5,  w: 12, h: 3, minW: 3, minH: 2 },
  { i: "perf",         x: 0, y: 8,  w: 12, h: 3, minW: 4, minH: 3 },
];

export const DEFAULT_LAYOUTS: Record<string, DashLayout> = {
  default: { name: "الرئيسي", grid: DEFAULT_GRID },
};

export function applyTheme(t: string) {
  const el = document.documentElement;
  el.classList.toggle("dark", t === "dark");
  el.classList.toggle("light", t === "light");
}

interface AppState {
  theme: "light" | "dark";
  sidebarOpen: boolean;
  currency: string;
  portfolioMode: "BUILD" | "MANAGEMENT";
  language: "ar" | "en";
  tickers: { tasi: boolean; brent: boolean };
  showClock: boolean;
  showMarketStatus: boolean;
  clockSeconds: boolean;
  clockHour12: boolean;
  clockDate: "greg" | "hijri" | "both";

  /* Workspace */
  activeLayout: string;
  layouts: Record<string, DashLayout>;

  /* Point 10 — customization everywhere */
  pageOrder: string[];
  hiddenPages: string[];
  startPage: string;
  portfolioCols: Record<string, boolean>;
  movePage: (id: string, dir: -1 | 1) => void;
  togglePage: (id: string) => void;
  setStartPage: (id: string) => void;
  applyServerLayout: (layout: { pageOrder?: string[]; hiddenPages?: string[]; startPage?: string; portfolioCols?: Record<string, boolean> } | null) => void;
  togglePortfolioCol: (id: string) => void;

  setTheme: (t: "light" | "dark") => void;
  setTicker: (k: "tasi" | "brent", v: boolean) => void;
  setShowClock: (v: boolean) => void;
  setShowMarketStatus: (v: boolean) => void;
  setClockSeconds: (v: boolean) => void;
  setClockHour12: (v: boolean) => void;
  setClockDate: (v: "greg" | "hijri" | "both") => void;
  toggleTheme: () => void;
  setSidebarOpen: (v: boolean) => void;
  setCurrency: (c: string) => void;
  setPortfolioMode: (m: "BUILD" | "MANAGEMENT") => void;
  setLanguage: (l: "ar" | "en") => void;

  setActiveLayout: (id: string) => void;
  saveGrid: (grid: GridItem[]) => void;
  addWidget: (widgetId: string, size: { w: number; h: number; minW?: number; minH?: number }) => void;
  removeWidget: (widgetId: string) => void;
  addLayout: (name: string) => void;
  renameLayout: (id: string, name: string) => void;
  deleteLayout: (id: string) => void;
  resetLayout: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: "light",
      sidebarOpen: true,
      currency: "SAR",
      portfolioMode: "BUILD",
      language: "ar",
      tickers: { tasi: true, brent: true },
      showClock: true,
      showMarketStatus: true,
      clockSeconds: false,     // الافتراضي: بلا ثواني (أهدأ بصريًّا)
      clockHour12: true,       // الافتراضي: نظام ١٢ ساعة
      clockDate: "both",

      activeLayout: "default",
      layouts: DEFAULT_LAYOUTS,

      pageOrder: ["portfolio", "market", "chart", "governance", "library", "ai", "calculators", "reports", "notifications", "settings"],
      hiddenPages: ["notifications"],   // الإشعارات مطفأة افتراضياً
      startPage: "portfolio",
      portfolioCols: { sector: true, shares: true, avgCost: true, lastPrice: true, marketValue: true, weight: true, pnl: true, dividends: false, actions: true },
      movePage: (id, dir) => set((s) => {
        const order = [...s.pageOrder];
        const i = order.indexOf(id);
        const j = i + dir;
        if (i < 0 || j < 0 || j >= order.length) return {};
        [order[i], order[j]] = [order[j], order[i]];
        _pushLayout({ pageOrder: order, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts: s.layouts, activeLayout: s.activeLayout });
        return { pageOrder: order };
      }),
      togglePage: (id) => set((s) => {
        if (id === "settings") return {}; // never hide settings
        const hidden = s.hiddenPages.includes(id)
          ? s.hiddenPages.filter(p => p !== id)
          : [...s.hiddenPages, id];
        const startPage = hidden.includes(s.startPage) ? "portfolio" : s.startPage;
        _pushLayout({ pageOrder: s.pageOrder, hiddenPages: hidden, startPage, layouts: s.layouts, activeLayout: s.activeLayout });
        return { hiddenPages: hidden, startPage };
      }),
      setStartPage: (id) => { const s = get(); _pushLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: id, layouts: s.layouts, activeLayout: s.activeLayout }); set({ startPage: id }); },
      /** يطبّق التخطيط المحفوظ على الخادم (يُستدعى مرّة عند الإقلاع) — يوحّد
       *  القائمة ولوحة التحكم عبر كل الأجهزة بدل اعتماد كل متصفح على نسخته. */
      applyServerLayout: (layout) => {
        if (!layout) return;
        const patch: any = {};
        if (Array.isArray(layout.pageOrder) && layout.pageOrder.length) {
          let order = [...layout.pageOrder];
          // الترتيب المحفوظ على الخادم قد يسبق «المكتبة» أو يضعها في موضع قديم؛
          // نضمن وجودها في موضعها الصحيح: بين الحوكمة والتحليل.
          order = order.filter((p) => p !== "library");
          const gi = order.indexOf("governance");
          order = gi >= 0 ? [...order.slice(0, gi + 1), "library", ...order.slice(gi + 1)] : [...order, "library"];
          patch.pageOrder = order;
        }
        /* ══ صفحةُ البداية مستقلّةٌ عن ترتيب القائمة ══
           كانت تُطبَّق **داخل** شرط `pageOrder` وحده: فمن غيّر صفحة البداية
           ولم يُعِد ترتيب القائمة، سقط اختيارُه صامتاً على أي جهازٍ لا
           يحمل نسخةً محلّية — يفتح التطبيق فيجد «المحفظة» مهما اختار.
           وهما إعدادان لا رابط بينهما: أحدهما ترتيبُ أقسام، والآخر أينَ
           يبدأ. فيُقرأ كلٌّ منهما بمفرده. */
        if (Array.isArray(layout.hiddenPages)) patch.hiddenPages = layout.hiddenPages;
        if (typeof layout.startPage === "string" && layout.startPage) {
          patch.startPage = layout.startPage;
        }
        // أعمدة الجدول: تُدمج فوق الافتراضي فلا يسقط عمودٌ أُضيف بعد الحفظ.
        if (layout.portfolioCols && typeof layout.portfolioCols === "object") {
          patch.portfolioCols = { ...get().portfolioCols, ...layout.portfolioCols };
        }
        // شبكة لوحة التحكم: يطابقها عبر الأجهزة (سبب اختفاء «نمو العائد» على
        // الكمبيوتر كان اختلاف الشبكة المحلية بين المتصفحات).
        if (layout.layouts && typeof layout.layouts === "object" && layout.layouts.default?.grid) {
          patch.layouts = layout.layouts;
          if (layout.activeLayout) patch.activeLayout = layout.activeLayout;
        }
        if (Object.keys(patch).length) set(patch);
      },
      /* أعمدة الجدول تعبر الأجهزة بأمر المالك: من يُخفي عمودَين على المكتب
         كان يفاجأ بهما على الجوّال، لأنها كانت تعيش في ذاكرة المتصفّح وحدها. */
      togglePortfolioCol: (id) => set((s) => {
        const portfolioCols = { ...s.portfolioCols, [id]: !s.portfolioCols[id] };
        _pushLayout({ portfolioCols });
        return { portfolioCols };
      }),

      setShowMarketStatus: (v) => set({ showMarketStatus: v }),
      setClockSeconds: (v) => set({ clockSeconds: v }),
      setClockHour12: (v) => set({ clockHour12: v }),
      setClockDate: (v) => set({ clockDate: v }),
      setTheme: (t) => {
        set({ theme: t });
        applyTheme(t);
      },
      toggleTheme: () => {
        get().setTheme(get().theme === "dark" ? "light" : "dark");
      },
      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      setCurrency: (c) => set({ currency: c }),
      setPortfolioMode: (m) => set({ portfolioMode: m }),
      setLanguage: (l) => {
        set({ language: l });
        document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
        // Pinned "en" (see App.tsx): unifies input digits Latin on all devices.
        document.documentElement.lang = "en";
      },

      setActiveLayout: (id) => { const s = get(); _pushLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts: s.layouts, activeLayout: id }); set({ activeLayout: id }); },
      saveGrid: (grid) => set((s) => {
        const layouts = { ...s.layouts, [s.activeLayout]: { ...s.layouts[s.activeLayout], grid } };
        _pushLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts, activeLayout: s.activeLayout });
        return { layouts };
      }),
      addWidget: (widgetId, size) => set((s) => {
        const cur = s.layouts[s.activeLayout];
        if (!cur || cur.grid.some(g => g.i === widgetId)) return {};
        const maxY = cur.grid.reduce((m, g) => Math.max(m, g.y + g.h), 0);
        const item: GridItem = { i: widgetId, x: 0, y: maxY, ...size };
        const layouts = { ...s.layouts, [s.activeLayout]: { ...cur, grid: [...cur.grid, item] } };
        _pushLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts, activeLayout: s.activeLayout });
        return { layouts };
      }),
      removeWidget: (widgetId) => set((s) => {
        const cur = s.layouts[s.activeLayout];
        const layouts = { ...s.layouts, [s.activeLayout]: { ...cur, grid: cur.grid.filter(g => g.i !== widgetId) } };
        _pushLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts, activeLayout: s.activeLayout });
        return { layouts };
      }),
      addLayout: (name) => set((s) => {
        const id = "custom_" + Date.now();
        return {
          layouts: { ...s.layouts, [id]: { name, grid: [] } },
          activeLayout: id,
        };
      }),
      renameLayout: (id, name) => set((s) => ({
        layouts: { ...s.layouts, [id]: { ...s.layouts[id], name } },
      })),
      deleteLayout: (id) => set((s) => {
        if (Object.keys(s.layouts).length <= 1) return {};
        const rest = { ...s.layouts };
        delete rest[id];
        return { layouts: rest, activeLayout: s.activeLayout === id ? Object.keys(rest)[0] : s.activeLayout };
      }),
      resetLayout: () => set((s) => {
        const def = DEFAULT_LAYOUTS[s.activeLayout];
        if (def) {
          return { layouts: { ...s.layouts, [s.activeLayout]: { ...def, grid: [...def.grid] } } };
        }
        return { layouts: { ...s.layouts, [s.activeLayout]: { ...s.layouts[s.activeLayout], grid: [] } } };
      }),
    }),
    {
      name: "sp-app-store",
      version: 24,
      migrate: (persisted: any) => {
        let order: string[] = persisted?.pageOrder ?? [];

        // "لوحة التحكم" is no longer a standalone sidebar page — its grid
        // moved into "المحفظة" as a tab, alongside "أخبار المحفظة"/"مفكرة
        // المحفظة"/"التنبيهات" tabs that used to live inside it. Drop the
        // now-gone sidebar entry and re-point anyone's start page at
        // portfolio instead of a route that no longer exists.
        order = order.filter((p: string) => p !== "dashboard");
        if (persisted?.startPage === "dashboard") persisted.startPage = "portfolio";

        // "wealth" band inside the لوحة التحكم grid duplicated the wealth
        // band صفحة المحفظة already shows above the tab bar now that the
        // grid lives there too — drop it from every saved layout and pull
        // whatever was below it up to fill the gap.
        {
          const gridLayouts = { ...(persisted?.layouts ?? {}) };
          for (const key of Object.keys(gridLayouts)) {
            const grid: GridItem[] = gridLayouts[key]?.grid ?? [];
            const wealth = grid.find((g) => g.i === "wealth");
            if (wealth) {
              gridLayouts[key] = {
                ...gridLayouts[key],
                grid: grid
                  .filter((g) => g.i !== "wealth")
                  .map((g) => (g.y >= wealth.y + wealth.h ? { ...g, y: g.y - wealth.h } : g)),
              };
            }
          }
          persisted = { ...persisted, layouts: gridLayouts };
        }
        if (!order.includes("calculators")) {
          order = [...order.filter((p: string) => p !== "reports"), "calculators", "reports"];
        }
        if (!order.includes("chart")) {
          const i = order.indexOf("market");
          if (i >= 0) order = [...order.slice(0, i + 1), "chart", ...order.slice(i + 1)];
          else order = [...order, "chart"];
        }
        // المكتبة تقع بين الحوكمة والتحليل. تُدرَج لمن لا يملكها، وتُنقَل لموضعها
        // الصحيح لمن كانت لديه بعد التقارير (من إصدار سابق).
        order = order.filter((p: string) => p !== "library");
        {
          const i = order.indexOf("governance");
          if (i >= 0) order = [...order.slice(0, i + 1), "library", ...order.slice(i + 1)];
          else order = [...order, "library"];
        }
        // "أخبار المحفظة"/"مفكرة المحفظة" moved from full nav pages to
        // Dashboard-internal tabs (beside الرئيسي) — drop the stray sidebar
        // entries for anyone who has them from that brief in-between state.
        order = order.filter((p: string) => p !== "portfolioNews" && p !== "portfolioCalendar");
        order = order.filter((v: string, i: number, a: string[]) => a.indexOf(v) === i);

        // Portfolio evaluation now lives in the AI page, not the dashboard grid —
        // strip any leftover "portfolioHealth" grid entry from saved layouts.
        const layouts = { ...(persisted?.layouts ?? {}) };
        for (const key of Object.keys(layouts)) {
          const grid: GridItem[] = layouts[key]?.grid ?? [];
          if (grid.some((g) => g.i === "portfolioHealth")) {
            layouts[key] = { ...layouts[key], grid: grid.filter((g) => g.i !== "portfolioHealth") };
          }
        }
        // Market value / invested / unrealized / dividends / liquidity / companies
        // are now compact inline stats inside the wealth band itself — drop the
        // now-redundant standalone cards from the DEFAULT ("الرئيسي") layout only
        // (the daily layout intentionally keeps its own standalone cards) and
        // give the wealth band the extra height it needs to show them.
        if (layouts["default"]) {
          const REDUNDANT_STAT_IDS = ["marketValue", "invested", "unrealized", "dividends", "liquidity", "companies"];
          const grid: GridItem[] = layouts["default"].grid ?? [];
          layouts["default"] = {
            ...layouts["default"],
            grid: grid
              .filter((g) => !REDUNDANT_STAT_IDS.includes(g.i))
              .map((g) => g.i === "wealth" ? { ...g, h: Math.max(g.h, 3), minH: 3 } : g),
          };
        }
        // "ملخص المحفظة" duplicated numbers already shown inline in the
        // wealth band's stat row (market value, liquidity, dividends, ...)
        // — drop it from the default layout too, and let "goals" take the
        // freed-up full row instead of sharing it with the now-gone card.
        if (layouts["default"]) {
          const grid: GridItem[] = layouts["default"].grid ?? [];
          if (grid.some((g) => g.i === "summary")) {
            layouts["default"] = {
              ...layouts["default"],
              grid: grid
                .filter((g) => g.i !== "summary")
                .map((g) => g.i === "goals" ? { ...g, x: 0, w: 12 } : g),
            };
          }
        }
        // "الأهداف الاستثمارية" and "توزيع القطاعات" swapped places — goals
        // now sits paired with "أداء المحفظة" (where sectors used to be),
        // and sectors took goals' old full-width bottom row. Re-sync anyone
        // whose persisted default layout still has the old arrangement.
        if (layouts["default"]) {
          const grid: GridItem[] = layouts["default"].grid ?? [];
          const goals = grid.find((g) => g.i === "goals");
          const sectors = grid.find((g) => g.i === "sectors");
          if (goals && sectors && goals.y > sectors.y) {
            layouts["default"] = {
              ...layouts["default"],
              grid: grid.map((g) => {
                if (g.i === "goals") return { ...g, x: sectors.x, y: sectors.y, w: sectors.w, minW: 3 };
                if (g.i === "sectors") return { ...g, x: 0, y: goals.y, w: 12 };
                return g;
              }),
            };
          }
        }

        // اليومي tab removed entirely — its market-pulse row moved onto
        // الرئيسي (below the wealth band), and the single-mover tiles
        // became three separate top-gainer/loser cards each. Drop the old
        // "daily" layout and splice the pulse row into "default" for
        // anyone who doesn't already have it there.
        if (layouts["daily"]) delete layouts["daily"];
        if (persisted?.activeLayout === "daily") persisted.activeLayout = "default";
        if (layouts["default"]) {
          const grid: GridItem[] = layouts["default"].grid ?? [];
          const PULSE_IDS = ["tasi", "brent", "gainer1", "gainer2", "gainer3", "loser1", "loser2", "loser3"];
          // "unrealized"/"liquidity" were briefly part of this row too, but
          // duplicated numbers already shown in the wealth band right above
          // it — the REDUNDANT_STAT_IDS pass above already strips those two
          // ids from the grid, so checking for their presence here would
          // never catch anyone; check tasi's now-stale narrow width instead
          // (it used to share the row 4-wide, now it should span half of it).
          const hasStale = grid.find((g) => g.i === "tasi")?.w !== 6;
          if (hasStale || !PULSE_IDS.every((id) => grid.some((g) => g.i === id))) {
            const kept = grid.filter((g) => !PULSE_IDS.includes(g.i) && g.i !== "topGainer" && g.i !== "topLoser" && g.i !== "unrealized" && g.i !== "liquidity" && g.i !== "wealth");
            const pulseDefaults = DEFAULT_GRID.filter((d) => PULSE_IDS.includes(d.i));
            // Normalize relative to whatever y the kept items already start
            // at — someone missing the pulse row entirely (old shape) needs
            // 3 rows of headroom made for it; someone who already had it
            // (just with the now-dropped unrealized/liquidity tiles) needs
            // none, since removing 2 tiles from an existing row doesn't
            // change how many rows that section occupies.
            const minKeptY = kept.length ? Math.min(...kept.map((g) => g.y)) : 6;
            const restNormalized = kept.map((g) => ({ ...g, y: g.y - minKeptY + 6 }));
            layouts["default"] = { ...layouts["default"], grid: [...grid.filter((g) => g.i === "wealth"), ...pulseDefaults, ...restNormalized] };
          }
        }

        // "نمو العائد" (Model ① return-growth curve) is a new default widget —
        // splice it into anyone's persisted default layout right after "أداء
        // المحفظة", making perf half-width to sit beside it, if they don't
        // already have it. New installs get it straight from DEFAULT_GRID.
        if (layouts["default"]) {
          const grid: GridItem[] = layouts["default"].grid ?? [];
          if (!grid.some((g) => g.i === "returngrowth")) {
            const perf = grid.find((g) => g.i === "perf");
            const y = perf ? perf.y : 3;
            layouts["default"] = {
              ...layouts["default"],
              grid: [
                ...grid.map((g) => g.i === "perf" ? { ...g, x: 0, w: 6, minW: 4, minH: 3 } : g),
                { i: "returngrowth", x: 6, y, w: 6, h: 3, minW: 4, minH: 3 },
              ],
            };
          }
        }

        // "التحليل" and "المراجعة الشهرية" tabs were dropped — their content is
        // already covered by "الرئيسي"/"اليومي", so remove them from anyone's
        // already-persisted layout list too, not just new installs.
        delete layouts["analysis"];
        delete layouts["review"];
        let activeLayout = persisted?.activeLayout;
        if (activeLayout === "analysis" || activeLayout === "review") activeLayout = "default";

        // Gold ticker → KSA ETF → weekly foreign-flow widget: the whole
        // lineage was removed (no reliable live source), so drop whatever
        // remains of it from anyone's already-persisted layout too.
        for (const key of Object.keys(layouts)) {
          const grid: GridItem[] = layouts[key]?.grid ?? [];
          if (grid.some((g) => g.i === "gold" || g.i === "ksa" || g.i === "flow")) {
            layouts[key] = { ...layouts[key], grid: grid.filter((g) => g.i !== "gold" && g.i !== "ksa" && g.i !== "flow") };
          }
        }
        // v20: تاسي/برنت أُزيلا من لوحة التحكم (يبقيان في شاشة السوق) — احذفهما
        // من كل تخطيط محفوظ واسحب ما تحتهما لأعلى ليملأ الفراغ.
        for (const key of Object.keys(layouts)) {
          const grid: GridItem[] = layouts[key]?.grid ?? [];
          if (grid.some((g) => g.i === "tasi" || g.i === "brent")) {
            const rows = grid.filter((g) => g.i === "tasi" || g.i === "brent");
            const rowH = Math.max(...rows.map((g) => g.h), 1);
            const rowY = Math.min(...rows.map((g) => g.y));
            layouts[key] = {
              ...layouts[key],
              grid: grid
                .filter((g) => g.i !== "tasi" && g.i !== "brent")
                .map((g) => (g.y > rowY ? { ...g, y: g.y - rowH } : g)),
            };
          }
        }

        // v21: إعادة ترتيب لوحة التحكم — نمو العائد + توزيع القطاعات في صفٍّ واحد
        // (يملأ القطاعُ الفراغَ بجانب العائد)، ثم الأهداف، ثم أداء المحفظة بعدها.
        for (const key of Object.keys(layouts)) {
          const grid: GridItem[] = layouts[key]?.grid ?? [];
          const has = (id: string) => grid.some(g => g.i === id);
          if (has("returngrowth") && has("sectors") && has("goals") && has("perf")) {
            const POS: Record<string, Partial<GridItem>> = {
              returngrowth: { x: 0, y: 2, w: 6, minW: 4, minH: 3 },
              sectors:      { x: 6, y: 2, w: 6, minW: 4, minH: 3 },
              goals:        { x: 0, y: 5, w: 12, minW: 3, minH: 2 },
              perf:         { x: 0, y: 8, w: 12, minW: 4, minH: 3 },
            };
            layouts[key] = {
              ...layouts[key],
              grid: grid.map(g => POS[g.i] ? { ...g, ...POS[g.i], h: Math.max(g.h, 3) } : g),
            };
          }
        }

        const tickers = { ...(persisted?.tickers ?? {}) };
        delete (tickers as any).gold;
        delete (tickers as any).ksa;
        delete (tickers as any).flow;

        // The "custom" theme/color-picker option was removed — anyone who
        // had it selected falls back to light.
        let theme = persisted?.theme === "custom" ? "light" : persisted?.theme;
        // v17: «أساسي» (royal) theme removed entirely (owner decision) —
        // anyone still on it falls back to light.
        if (theme === "royal") theme = "light";
        delete (persisted as any)?.royalIntroduced;

        // v24: الافتراضيات المعتمدة **تُفرض** الآن ولا تُترك لما خزّنه المتصفح
        // في أول تشغيل. v23 كانت تحترم أي تفضيل محفوظ، فبقيت الإشعارات ظاهرة
        // على الأجهزة التي فُتح فيها التطبيق قبل اعتماد الافتراضي — وهذا ما
        // رآه المالك. الفرض هنا لمرّة واحدة (بترقية النسخة) لا في كل إقلاع،
        // فيبقى بإمكانه إظهارها بعدها من «ترتيب الصفحات» ولا نلغي اختياره ثانيةً.
        const prevHidden: string[] = Array.isArray(persisted?.hiddenPages) ? persisted.hiddenPages : [];
        const hiddenPages = prevHidden.includes("notifications")
          ? prevHidden : [...prevHidden, "notifications"];

        // v22: الافتراضي المعتمد للساعة — إظهار الساعة والحالة، بلا ثواني،
        // نظام ١٢ ساعة. نفرضه على النسخ المحفوظة سابقاً (كانت الثواني مفعّلة).
        const clockSeconds = false;
        const clockHour12 = persisted?.clockHour12 ?? true;
        const showClock = persisted?.showClock ?? true;
        const showMarketStatus = persisted?.showMarketStatus ?? true;

        return {
          ...persisted,
          activeLayout,
          theme,
          showClock, showMarketStatus, clockSeconds, clockHour12,
          hiddenPages,
          clockDate: persisted?.clockDate ?? "both",
          tickers: Object.keys(tickers).length ? tickers : persisted?.tickers,
          pageOrder: order,
          layouts: Object.keys(layouts).length ? layouts : persisted?.layouts,
          portfolioCols: {
            sector: true, shares: true, avgCost: true, lastPrice: true,
            marketValue: true, weight: true, pnl: true, dividends: false, actions: true,
            ...(persisted?.portfolioCols ?? {}),
          },
        };
      },
    }
  )
);
