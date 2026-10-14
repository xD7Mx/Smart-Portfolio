import React, { useState, useEffect, useRef } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Briefcase, TrendingUp, Brain,
  FileText, Bell, Settings, Calculator,
  Menu, X, CandlestickChart, Book, Activity } from "lucide-react";
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
  // ‏D687: «غرفة التداول» بأيقونة الرسم البياني، والرسمُ تبويبٌ داخلها (كان قسماً هنا) — ‏D677: مكانَ مختبر الأبحاث
  watchlist:     { to: "/watchlist",     icon: CandlestickChart, key: "nav.watchlist" },
  // ‏D694: «الحوكمة» تبويبٌ في المحفظة (مكانَ المختبر) — لا قسمَ لها هنا
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
  const [drawer, setDrawerRaw] = useState(false); // mobile off-canvas
  /* ‏D687: الحركةُ هويّة — القائمةُ تنزلق خارجةً كما دخلت، لا تختفي فجأة */
  const [closing, setClosing] = useState(false);
  /* ‏D712: «تتبعُ حركةَ الإصبع» — `manual`: القائمةُ يحرّكها السحبُ لا حركةٌ محفوظة (فلا تُعاد حركةُ الدخول بعد أن استقرّت) */
  const [manual, setManual] = useState(false);
  const drawerRef = useRef(false);
  const asideRef = useRef<HTMLElement | null>(null);
  const scrimRef = useRef<HTMLDivElement | null>(null);
  const progRef = useRef(0);
  const setDrawer = (v: boolean) => {
    if (v) { setManual(false); setClosing(false); drawerRef.current = true; setDrawerRaw(true); return; }
    if (!drawerRef.current) return;
    drawerRef.current = false;
    setManual(false);
    setClosing(true);
    setTimeout(() => { setDrawerRaw(false); setClosing(false); }, 180);
  };
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

  /* ══ إيماءةُ السحب ══ (بأمر المالك · D687 · D712): على الجوال، سحبُ الإصبع من اليمين إلى اليسار يُخرج القائمةَ الجانبية
     (وفي الواجهة الإنجليزية عكسُه)، والسحبُ المعاكس يُعيدها. ‏D712 (المالك): «بدلاً من أن تكون قاسية اجعلها تتبع حركةَ الإصبع
     عند السحب ولو بدايةَ رأس القائمة» — فالقائمةُ تخرج بقدر ما يسحب الإصبعُ (حافّتُها أوّلاً)، والغطاءُ يغمق معها، وعناصرُها
     تلحقها بتأخّرٍ خفيف؛ وعند الرفع تستقرّ مفتوحةً أو مغلقةً بالمسافة والسرعة بحركةٍ ناعمة. والحكمُ أفقيٌّ أوّلاً: التمريرُ
     الرأسيّ والضغطةُ المطوّلة لترتيب البطاقات لا يحرّكانها، ولا تبدأ من حقلٍ أو رسمٍ أو شريطٍ يتمرّر أفقياً. */
  useEffect(() => {
    const W = 256;                                             // عرضُ القائمة (‏w-64)
    const sign = isRtl ? -1 : 1;                               // اتّجاهُ الفتح على محور الإصبع
    const reduced = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let x0 = 0, y0 = 0, t0 = 0, armed = false, mode: "" | "open" | "close" = "", lastX = 0, lastT = 0, vel = 0, raf = 0;
    const blocked = (el: Element | null) => {
      for (let i = 0; el && i < 10; i++, el = el.parentElement) {
        if (el.matches("input,textarea,select,canvas,svg,[contenteditable],[data-noswipe]")) return true;
        const ox = getComputedStyle(el).overflowX;
        if ((ox === "auto" || ox === "scroll") && el.scrollWidth > el.clientWidth + 1) return true;
      }
      return false;
    };
    const paint = (p: number, settle = false) => {
      progRef.current = p;
      const a = asideRef.current, sc = scrimRef.current;
      const dur = settle && !reduced() ? ".34s cubic-bezier(.22,1,.36,1)" : "";
      if (a) {
        a.style.transition = dur ? `transform ${dur}` : "none";
        a.style.transform = `translateX(${(isRtl ? 1 : -1) * (1 - p) * 100}%)`;
        a.style.setProperty("--dp", String(p));
        a.style.setProperty("--dp-t", dur ? `transform ${dur}, opacity ${dur}` : "none");
      }
      if (sc) { sc.style.transition = dur ? `opacity ${dur}` : "none"; sc.style.opacity = String(p); }
    };
    const onStart = (e: TouchEvent) => {
      armed = window.innerWidth < 768 && e.touches.length === 1 && !blocked(e.target as Element);
      mode = "";
      if (!armed) return;
      x0 = lastX = e.touches[0].clientX; y0 = e.touches[0].clientY; t0 = lastT = performance.now(); vel = 0;
    };
    const onMove = (e: TouchEvent) => {
      if (!armed) return;
      const x = e.touches[0].clientX, dx = x - x0, dy = e.touches[0].clientY - y0;
      if (!mode) {
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
        if (Math.abs(dy) > Math.abs(dx) * 0.8) { armed = false; return; }          // رأسيٌّ: تمريرٌ لا سحب
        if (performance.now() - t0 > 320) { armed = false; return; }              // إصبعٌ ثبت ثمّ تحرّك: ضغطةٌ مطوّلةٌ لترتيب البطاقات
        const opening = Math.sign(dx) === sign;
        if (opening && !drawerRef.current) {
          mode = "open"; drawerRef.current = true; progRef.current = 0;
          setManual(true); setClosing(false); setDrawerRaw(true);
        } else if (!opening && drawerRef.current && !closing) {
          mode = "close"; setManual(true);
        } else { armed = false; return; }
      }
      const t = performance.now();
      if (t > lastT) vel = 0.6 * vel + 0.4 * ((x - lastX) / (t - lastT));
      lastX = x; lastT = t;
      const travel = (dx * sign) / W;                                               // موجبٌ نحو الفتح
      const p = Math.max(0, Math.min(1, mode === "open" ? travel : 1 + travel));
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => paint(p));
    };
    const onEnd = () => {
      if (!armed || !mode) { armed = false; return; }
      armed = false;
      cancelAnimationFrame(raf);
      const v = performance.now() - lastT > 90 ? 0 : vel * sign;                   // إصبعٌ توقّف ثمّ رُفع: لا اندفاع
      const p = progRef.current;
      const open = v > 0.35 ? true : v < -0.35 ? false : p > (mode === "open" ? 0.4 : 0.6);
      mode = "";
      paint(open ? 1 : 0, true);
      const done = () => {
        if (open) { drawerRef.current = true; return; }
        // خرجت مع الإصبع فعلاً: لا نسخةَ خروجٍ تُعيد انزلاقَها من موضع الفتح (‏exitMotion · D616)
        asideRef.current?.parentElement?.setAttribute("data-noghost", "");
        drawerRef.current = false; setDrawerRaw(false); setManual(false);
      };
      if (reduced()) done(); else setTimeout(done, 360);
    };
    document.addEventListener("touchstart", onStart, { passive: true });
    document.addEventListener("touchmove", onMove, { passive: true });
    document.addEventListener("touchend", onEnd, { passive: true });
    document.addEventListener("touchcancel", onEnd, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("touchstart", onStart); document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", onEnd); document.removeEventListener("touchcancel", onEnd);
    };
  }, [isRtl, closing]);
  /* أوّلُ إطارٍ بعد التركيب بالسحب: القائمةُ عند موضع الإصبع لا عند حركة الدخول المحفوظة */
  React.useLayoutEffect(() => {
    if (!drawer || !manual) return;
    const a = asideRef.current, sc = scrimRef.current, p = progRef.current;
    if (a && !a.style.transform) {
      a.style.transition = "none";
      a.style.transform = `translateX(${(isRtl ? 1 : -1) * (1 - p) * 100}%)`;
      a.style.setProperty("--dp", String(p));
    }
    if (sc && !sc.style.opacity) { sc.style.transition = "none"; sc.style.opacity = String(p); }
  }, [drawer, manual, isRtl]);

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
          <div className={"drawer-pop md:hidden fixed inset-0 z-50" + (closing ? " drawer-closing" : "") + (manual ? " drawer-drag" : "")}
               onClick={() => setDrawer(false)}>
            <div ref={scrimRef} className="drawer-scrim absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <aside ref={asideRef} dir={isRtl ? "rtl" : "ltr"} style={{ ["--drawer-from" as any]: isRtl ? "100%" : "-100%",
                                                                        ["--dsign" as any]: isRtl ? 1 : -1 }}
              className={`mobile-drawer drawer-safe absolute top-0 ${isRtl ? "right-0" : "left-0"} h-full w-64 bg-[var(--field)] ${isRtl ? "border-l" : "border-r"} border-[var(--hairline)] flex flex-col ${manual ? "" : closing ? "drawer-out" : "drawer-in"}`}
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
            {/* D615: الانتقالُ بين الصفحات يتلاشى وينزلق انزلاقاً خفيفاً بدل القفز */}
            <div key={location.pathname} className="route-in"><Outlet /></div>
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
