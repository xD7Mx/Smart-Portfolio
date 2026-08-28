import React, { useState, useEffect, useRef } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Briefcase, TrendingUp, Brain,
  FileText, Bell, Settings, Shield, Calculator,
  Menu, X, CandlestickChart, Book, Activity
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { notificationsApi } from "../../services/api";
import { useT } from "../../i18n";
import { useAppStore } from "../../store/appStore";
import Logo from "./Logo";
import MarketTicker from "./MarketTicker";
import LiveClock from "./LiveClock";
import ChatBot from "./ChatBot";
import UpdateToast from "./UpdateToast";

export const PAGES: Record<string, { to: string; icon: any; key: string }> = {
  portfolio:     { to: "/portfolio",     icon: Briefcase,        key: "nav.portfolio" },
  market:        { to: "/market",        icon: TrendingUp,       key: "nav.market" },
  chart:         { to: "/chart",         icon: CandlestickChart, key: "nav.chart" },
  governance:    { to: "/governance",    icon: Shield,           key: "nav.governance" },
  library:       { to: "/library",       icon: Book,             key: "nav.library" },
  ai:            { to: "/ai",            icon: Brain,            key: "nav.ai" },
  calculators:   { to: "/calculators",   icon: Calculator,       key: "nav.calculators" },
  reports:       { to: "/reports",       icon: FileText,         key: "nav.reports" },
  notifications: { to: "/notifications", icon: Bell,             key: "nav.notifications" },
  settings:      { to: "/settings",      icon: Settings,         key: "nav.settings" },
};

export default function MainLayout() {
  const [collapsed] = useState(true);  // pinned rail — expands on hover (toggle arrow removed)
  const [hovered, setHovered] = useState(false);
  const [drawer, setDrawer] = useState(false); // mobile off-canvas
  const expanded = !collapsed || hovered;
  const t = useT();
  const location = useLocation();
  const { language, pageOrder, hiddenPages } = useAppStore();
  const isRtl = language === "ar";

  // ── حفظ/استعادة موضع القراءة لكل صفحة ─────────────────────────────────
  // فتح خبر يخرج من التطبيق (وفي وضع PWA يُعاد تحميل الواجهة كاملةً عند
  // الرجوع)، فكان موضع القراءة يُفقد ويعود المستخدم لأعلى الصفحة. نُخزّن
  // موضع تمرير الحاوية الرئيسة في sessionStorage (يصمد أمام إعادة التحميل
  // الكامل، لا الذاكرة فقط) ونستعيده عند العودة لنفس المسار.
  const mainRef = useRef<HTMLElement>(null);
  const scrollKey = `scroll:${location.pathname}`;

  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    // استعادة: بعد رسم محتوى الصفحة (إطارين) حتى يكون الطول النهائي متاحاً.
    const saved = parseInt(sessionStorage.getItem(scrollKey) || "0", 10);
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => { if (saved > 0) el.scrollTop = saved; });
    });
    // حفظ مستمرّ (مخفّف) + عند إخفاء الصفحة/الخروج منها.
    let tick: ReturnType<typeof setTimeout> | null = null;
    const remember = () => sessionStorage.setItem(scrollKey, String(el.scrollTop));
    const onScroll = () => {
      if (tick) return;
      tick = setTimeout(() => { tick = null; remember(); }, 150);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("pagehide", remember);
    document.addEventListener("visibilitychange", remember);
    return () => {
      cancelAnimationFrame(raf1); cancelAnimationFrame(raf2);
      if (tick) clearTimeout(tick);
      remember();                         // احفظ قبل مغادرة المسار
      el.removeEventListener("scroll", onScroll);
      window.removeEventListener("pagehide", remember);
      document.removeEventListener("visibilitychange", remember);
    };
  }, [scrollKey]);

  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn:  () => notificationsApi.list().then(r => r.data.data),
    refetchInterval: 60000,
  });
  const unread = notifData?.filter((n: any) => n.status === "UNREAD").length ?? 0;

  /* ترتيب الصفحات محفوظٌ في متصفّح المالك من جلساتٍ سابقة، فأي صفحة تُضاف
     لاحقاً لا تكون فيه — فتُبنى الميزة ولا تظهر أبداً لمن يستعمل التطبيق منذ
     قبلها، وهو أسوأ أنواع الأعطال: لا خطأ ولا أثر، فقط غياب. نُلحق كل صفحة
     معروفة غائبة عن الترتيب المحفوظ بآخره، ما لم يكن المالك قد أخفاها عمداً. */
  const known = Object.keys(PAGES);
  const ordered = [...pageOrder, ...known.filter(id => !pageOrder.includes(id))];
  const navIds = ordered.filter(id => PAGES[id] && !hiddenPages.includes(id));

  // close the mobile drawer on navigation
  useEffect(() => { setDrawer(false); }, [location.pathname]);

  const Brand = ({ compact = false }: { compact?: boolean }) => (
    // Client-side navigation to the dashboard — plain <a>/window.location would
    // force a full page reload; NavLink keeps it an instant in-app transition.
    // وفي الوضع المضغوط كان الهدف 30×30 — دون أرضية اللمس (32). حدٌّ أدنى
    // للهدف بلا تكبير الشعار نفسه.
    <NavLink to="/portfolio" onClick={() => setDrawer(false)}
      className="press flex items-center gap-3" style={{ minWidth: 32, minHeight: 32 }}>
      <Logo size={compact ? 30 : 36} />
      {!compact && (
        <div>
          <p className="text-sm font-extrabold text-[var(--ink)] tracking-tight">{t("app.name")}</p>
          <p className="text-[10px] font-semibold" style={{
            background: "linear-gradient(90deg, var(--brand-a), var(--brand-b))",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>حلّل أكثر… قرّر بنفسك</p>
        </div>
      )}
    </NavLink>
  );

  const NavItems = ({ showLabels }: { showLabels: boolean }) => (
    <>
      {navIds.map(id => {
        const { to, icon: Icon, key } = PAGES[id];
        return (
          <NavLink key={to} to={to} onClick={() => setDrawer(false)}
            className={({ isActive }) => "nav-link" + (isActive ? " nav-active" : "")}>
            <div className="relative shrink-0">
              <Icon size={18} />
              {id === "notifications" && unread > 0 && (
                <span className="notif-count absolute -top-1 -right-1 min-w-[16px] h-4 px-[3px] bg-[var(--neg-ink)] text-[10px] rounded-full flex items-center justify-center leading-none">
                  {unread}
                </span>
              )}
            </div>
            {/* بلا `font-medium`: الوزن يُورَّث من الرابط، فيثقل مع اختياره.
                فرضُ وزنٍ هنا كان يقطع الوراثة ويُلغي أثر الاختيار. */}
            {showLabels && <span>{t(key)}</span>}
          </NavLink>
        );
      })}
    </>
  );

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="app-shell flex flex-col h-screen overflow-hidden bg-[var(--bg)]">
      {/* Top identity bar — logo + app name, always visible above the ticker.
          `app-topbar` adds env(safe-area-inset-top) so the menu/bell buttons
          clear the iOS status bar/notch (black-translucent lets the app draw
          full-screen; without this inset the buttons hid under the status bar
          — regressed by the orientation/launch fix). Adapts on rotation too. */}
      {/* ثلاث خانات متوازنة: البداية (قائمة/شعار) · الوسط (الساعة) · النهاية
          (الإشعارات). الخانتان الجانبيتان flex-1 متساويتان فتتمركز الساعة
          فعليًّا في المنتصف على الجوال والكمبيوتر معاً، والجرس في الطرف
          الأيسر بصريًّا (نهاية الاتجاه في RTL). */}
      <div className="app-topbar flex items-center gap-3 px-4 shrink-0 panel border-b border-[var(--hairline)]">
        <div className="flex-1 flex items-center gap-3 min-w-0">
          <button onClick={() => setDrawer(true)} className="md:hidden text-[var(--ink)] hover:text-[var(--ink)] p-1"><Menu size={22} /></button>
          {/* الشعار يُخفى على الجوال — كان يزاحم زر القائمة (الخطوط الثلاثة)؛
              يبقى ظاهراً على الشاشات المتوسطة فما فوق وداخل درج الجوال نفسه. */}
          <div className="hidden md:block"><Brand compact /></div>
        </div>

        {/* الساعة الرسمية (توقيت مكة) + حالة السوق — في المنتصف دائماً */}
        <LiveClock />

        <div className="flex-1 flex items-center justify-end">
          <NavLink to="/notifications" className="press relative shrink-0 text-[var(--ink)] hover:text-[var(--ink)] p-1">
            <Bell size={20} />
            {unread > 0 && <span className="notif-count absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-[3px] bg-[var(--neg-ink)] text-[10px] rounded-full flex items-center justify-center leading-none">{unread}</span>}
          </NavLink>
        </div>
      </div>

      {/* News ticker — right below the app name, not above the whole app */}
      {/* شريطٌ واحد يحمل الأسعار والأخبار معاً — بقرار المالك. */}
      <MarketTicker />

      <div className="app-body flex flex-1 overflow-hidden">
        {/* Desktop sidebar — auto-collapses to an icon rail and expands on hover
            so it stays out of the way until needed. */}
        <aside
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className={`app-sidebar hidden md:flex flex-col ${isRtl ? "border-l" : "border-r"} border-[var(--hairline)] bg-[var(--field)] transition-all duration-200 ${expanded ? "w-56" : "w-16"}`}>
          <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
            <NavItems showLabels={expanded} />
          </nav>
        </aside>

        {/* Mobile drawer */}
        {drawer && (
          <div className="md:hidden fixed inset-0 z-50" onClick={() => setDrawer(false)}>
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <aside dir={isRtl ? "rtl" : "ltr"}
              className={`mobile-drawer drawer-safe absolute top-0 ${isRtl ? "right-0" : "left-0"} h-full w-64 bg-[var(--field)] ${isRtl ? "border-l" : "border-r"} border-[var(--hairline)] flex flex-col drawer-in`}
              onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-4 py-4 border-b border-[var(--hairline)]">
                <Brand />
                <button onClick={() => setDrawer(false)} className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
              </div>
              <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto"><NavItems showLabels /></nav>
            </aside>
          </div>
        )}

        {/* Main */}
        <main ref={mainRef} className="app-main flex-1 overflow-y-auto flex flex-col">
          <div className="p-3 sm:p-5 lg:p-6 max-w-[1600px] w-full mx-auto flex-1">
            <Outlet />
            <footer className="sp-footer">حقوق النشر محفوظة لـ D7M ©</footer>
          </div>
        </main>
      </div>

      {/* مساعد المحفظة — فقاعة عائمة فوق كل الصفحات (قراءة فقط) */}
      <ChatBot />
      <UpdateToast />
    </div>
  );
}
