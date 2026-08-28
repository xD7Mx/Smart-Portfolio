/**
 * Dashboard — fixed layout, no drag/resize/add/hide. Switch between the
 * pre-built "الرئيسي" grid view and three content tabs (أخبار المحفظة /
 * مفكرة المحفظة / التنبيهات) that replaced the removed اليومي tab.
 */
import React, { useState } from "react";
import { GridLayout, useContainerWidth, verticalCompactor } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import { LayoutGrid } from "lucide-react";
import { useAppStore, GridItem } from "../store/appStore";
import { WIDGET_MAP } from "../widgets/Widgets";
import PortfolioNewsPage from "./PortfolioNewsPage";
import PortfolioCalendarPage from "./PortfolioCalendarPage";
import NotificationsPage from "./NotificationsPage";

const EXTRA_TABS: { id: string; name: string; Component: React.ComponentType }[] = [
  { id: "portfolioNews",     name: "أخبار المحفظة",  Component: PortfolioNewsPage },
  { id: "portfolioCalendar", name: "مفكرة المحفظة",  Component: PortfolioCalendarPage },
  { id: "notifications",     name: "التنبيهات",       Component: NotificationsPage },
];

const MOBILE_BREAKPOINT = 680;
const TABLET_BREAKPOINT = 1024;
const TABLET_COLS = 6;

/**
 * Mobile default reflow: small stat cards (h<=1) pair two-per-row, larger
 * widgets (charts/lists) take the full width one-per-row — same order as the
 * active layout. Every section reflows automatically for phones without any
 * manual dragging.
 */
function mobileReflow(grid: GridItem[]): GridItem[] {
  const items = [...grid].sort((a, b) => (a.y - b.y) || (a.x - b.x));
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

/**
 * Tablet reflow: the desktop grid is authored against 12 columns, so a
 * widget with e.g. minW:6 (half a desktop row) fits fine at 1280px+ but
 * turns into a cramped sliver at 768-1024px if forced into the same
 * 12-column grid. Halve every column value onto a 6-column grid instead —
 * same relative proportions, roomier absolute width — and let the existing
 * compactor resolve any y-overlap the rounding introduces.
 */
function tabletReflow(grid: GridItem[]): GridItem[] {
  return grid.map(it => ({
    ...it,
    x: Math.round(it.x / 2),
    w: Math.max(1, Math.min(TABLET_COLS, Math.round(it.w / 2))),
  }));
}

/**
 * The grid container renders dir="ltr" (react-grid-layout computes pixel
 * offsets left-to-right internally, with no built-in RTL mode) — so column
 * 0 always lands on the physical left edge regardless of the page's own
 * RTL direction. Arabic reads right-to-left, so cards should visually fill
 * starting from the right: mirror every item's x within its row's column
 * count (x' = cols - x - w) right before rendering, flipping the physical
 * order without touching how the layouts are authored/persisted.
 */
function mirrorRtl(grid: GridItem[], cols: number): GridItem[] {
  return grid.map(it => ({ ...it, x: cols - it.x - it.w }));
}

export default function DashboardPage() {
  const { activeLayout, layouts, setActiveLayout } = useAppStore();
  const { width, containerRef, mounted } = useContainerWidth();
  const [activeTab, setActiveTab] = useState<string>("default");

  const layout = layouts[activeLayout] ?? Object.values(layouts)[0];
  const grid = layout?.grid ?? [];

  const isMobile = mounted && width > 0 && width < MOBILE_BREAKPOINT;
  const isTablet = mounted && width >= MOBILE_BREAKPOINT && width < TABLET_BREAKPOINT;
  const reflowedGrid = isMobile ? mobileReflow(grid) : isTablet ? tabletReflow(grid) : grid;
  const cols = isMobile ? 2 : isTablet ? TABLET_COLS : 12;
  const renderGrid = mirrorRtl(reflowedGrid, cols);

  const ExtraTabContent = EXTRA_TABS.find(t => t.id === activeTab)?.Component;

  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)]">لوحة التحكم</h1>
        <p className="text-[var(--ink-muted)] text-sm mt-0.5">نظرة شاملة على محفظتك</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        <LayoutGrid size={14} className="text-[var(--ink-muted)]" />
        {Object.entries(layouts).map(([id, l]) => (
          <button key={id}
            onClick={() => { setActiveLayout(id); setActiveTab("default"); }}
            className={activeTab === "default" && activeLayout === id
              ? "px-3 py-1.5 rounded-lg text-xs font-bold text-[var(--brand-ink)]"
              : "px-3 py-1.5 rounded-lg text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"}
            style={activeTab === "default" && activeLayout === id ? {background: "transparent,rgba(139,92,246,.12))", border: "1px solid rgba(59,130,246,.3)"} : {background: "var(--panel)"}}>
            {l.name}
          </button>
        ))}
        {EXTRA_TABS.map(t => (
          <button key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={activeTab === t.id
              ? "px-3 py-1.5 rounded-lg text-xs font-bold text-[var(--brand-ink)]"
              : "px-3 py-1.5 rounded-lg text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"}
            style={activeTab === t.id ? {background: "transparent,rgba(139,92,246,.12))", border: "1px solid rgba(59,130,246,.3)"} : {background: "var(--panel)"}}>
            {t.name}
          </button>
        ))}
      </div>

      {ExtraTabContent && <ExtraTabContent />}

      {/* Kept mounted (just hidden) instead of unmounted behind a ternary —
          the width-tracking ResizeObserver attaches to this div's node once
          on first mount and never reattaches, so unmounting/remounting it
          on every tab switch left it observing a detached node and frozen
          at a stale width the next time it reappeared (cards rendered
          shrunk until an actual window resize forced a re-measure). */}
      <div ref={containerRef} dir="ltr" style={{ display: ExtraTabContent ? "none" : undefined }}>
        {mounted && grid.length > 0 && (
          <GridLayout
            width={width}
            layout={renderGrid as any}
            gridConfig={isMobile
              ? { cols: 2, rowHeight: 120, margin: [10, 10] }
              : isTablet
              ? { cols: TABLET_COLS, rowHeight: 120, margin: [10, 10] }
              : { cols: 12, rowHeight: 120, margin: [12, 12] }}
            dragConfig={{ enabled: false }}
            resizeConfig={{ enabled: false }}
            compactor={verticalCompactor}
          >
            {renderGrid.map(item => {
              const def = WIDGET_MAP[item.i];
              if (!def) return <div key={item.i} style={{display:"none"}} />;
              const C = def.component;
              return (
                <div key={item.i} className="mc" style={{overflow: "auto", display: "flex", flexDirection: "column"}} dir="rtl">
                  <div className="flex-1 min-h-0"><C /></div>
                </div>
              );
            })}
          </GridLayout>
        )}
      </div>
    </div>
  );
}
