import React, { Suspense, useEffect, useState } from "react";
import { installExitMotion } from "./utils/exitMotion";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAppStore, applyTheme } from "./store/appStore";
import { settingsApi } from "./services/api";

// Layout
import MainLayout from "./components/common/MainLayout";
import { useAuthStore } from "./store/authStore";
import { useIdleLock } from "./hooks/useIdleLock";
import { enableAutoEnglish, disableAutoEnglish } from "./i18n-auto";

/** قفل كامل: التطبيق كله خلف جلسة المالك — بلا توكن يُحوَّل فوراً لشاشة
 * الدخول ولا يُحمَّل أي محتوى (لا «قراءة عامة» بعد الآن، بقرار المالك). */
function AuthGate() {
  const isOwner = useAuthStore(s => s.isOwner);
  if (!isOwner) return <Navigate to="/login" replace />;
  return <MainLayout />;
}

// Pages
/* ‏D814 (المالك 2026-11-24: «التطبيقُ يأخذ وقتاً عند التحميل — خلِّه سريعاً»): كانت الصفحاتُ كلُّها (المحفظةُ والسوقُ والشركةُ والمكتبة…)
   تُنزَّل وتُحلَّل قبل أن تظهر الأولى. فكلُّ صفحةٍ ملفٌّ وحدها يُنزَّل حين تُفتح، والباقي يُجلب في وقت الفراغ بعد ظهور الأولى —
   فالفتحُ الأوّلُ أخفّ، والتنقّلُ بعده فوريٌّ كما كان. */
const pageLoaders = {
  portfolio: () => import("./pages/PortfolioPage"), company: () => import("./pages/CompanyPage"), market: () => import("./pages/MarketPage"),
  reports: () => import("./pages/ReportsPage"), library: () => import("./pages/LibraryPage"), notifications: () => import("./pages/NotificationsPage"),
  settings: () => import("./pages/SettingsPage"), ai: () => import("./pages/AIPage"), calculators: () => import("./pages/CalculatorsPage"),
  watchlist: () => import("./pages/WatchlistPage"),
};
const PortfolioPage = React.lazy(pageLoaders.portfolio);
const CompanyPage = React.lazy(pageLoaders.company);
const MarketPage = React.lazy(pageLoaders.market);
const ReportsPage = React.lazy(pageLoaders.reports);
const LibraryPage = React.lazy(pageLoaders.library);
const NotificationsPage = React.lazy(pageLoaders.notifications);
const SettingsPage = React.lazy(pageLoaders.settings);
const AIPage = React.lazy(pageLoaders.ai);
const CalculatorsPage = React.lazy(pageLoaders.calculators);
const WatchlistPage = React.lazy(pageLoaders.watchlist);
import LoginPage       from "./pages/LoginPage";

/** بعد ظهور الصفحة الأولى: البقيةُ تُجلب في وقت الفراغ واحدةً بعد أخرى — فلا ينتظر التنقّلُ شبكة */
let warmed = false;
export function warmPages() {
  if (warmed) return;
  warmed = true;
  const list = Object.values(pageLoaders);
  const idle = (cb: () => void) => ((window as any).requestIdleCallback ? (window as any).requestIdleCallback(cb, { timeout: 4000 }) : window.setTimeout(cb, 1200));
  const next = () => { const f = list.shift(); if (f) f().catch(() => {}).finally(() => idle(next)); };
  idle(next);
}

// Styles
import "./styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      /* «الأقسام تُحمَّل متأخرة»: كانت البيانات تُعدّ قديمة بعد 30 ثانية،
         فكل عودةٍ إلى قسمٍ زرتَه قبل قليل تُعيد الجلب وتُظهر الهياكل من
         جديد وكأن الشاشة تُبنى أول مرة. والخادم يُخزّن الأسعار **15 دقيقة**
         (حدّ التأخير المسموح للسوق)، فما بعد ذلك جلبٌ لا يأتي بجديد.
         خمس دقائق تجعل التنقّل بين الأقسام فوريّاً من الذاكرة، ولا تُفوّت
         تحديثاً حقيقياً — وأفعالك أنت (شراء/بيع/إيداع) تُبطل الاستعلامات
         المعنيّة صراحةً فتظهر فوراً بلا انتظار. */
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      /* الاستجلاب الدوري كل دقيقة كان يفوق كاش الخادم خمسة عشر ضعفاً:
         خمسة عشر طلباً لا يمكن لأيٍّ منها أن يحمل سعراً أحدث من الأول. */
      refetchInterval: 5 * 60 * 1000,
      refetchIntervalInBackground: false,
    },
  },
});

/**
 * صفحة البداية — تحترم اختيار المالك في «التخصيص».
 *
 * كان هنا عطبان اجتمعا فبدا الاختيار كأنه لا يعمل:
 *  ١) `manifest.start_url` كان مثبَّتاً على `/portfolio`، فالتطبيق المثبَّت
 *     على الشاشة الرئيسية يبدأ عند المحفظة مباشرةً ولا يمرّ بهذا المسار
 *     أصلاً — فلا يُسأل الاختيار. صار الجذر `/`.
 *  ٢) وهنا: التحويل كان يقع فور الإقلاع بالقيمة المحلّية، والتخطيط المحفوظ
 *     على الخادم يصل بعده بلحظة — فيسبق التحويلُ الجوابَ. على جهازٍ جديد
 *     (أو بعد مسح بيانات المتصفّح) يذهب إلى المحفظة دائماً مهما اخترت.
 *
 * الآن ينتظر وصول التخطيط، بمهلة ١٫٥ ثانية فإن تأخّر الخادم لا يبقى المالك
 * أمام صفحةٍ فارغة: يمضي بالقيمة المحلّية. الانتظار للصواب لا للتعليق.
 */
let layoutLoaded = false;

/* ══ التطبيق يعود إلى مكانه الأخير ══ (بأمر المالك)
   يفتح رابطاً من التطبيق — خبراً أو صفحة «أرقام» — فيغادره المتصفّح، ثم
   يعود فيجد التطبيق قد أُقلع من أوّله: صفحةَ البداية بدل الشاشة التي كان
   فيها، والتمرير من رأس الصفحة. والسبب أن ويب-فيو الجوّال يُخلي الصفحة
   حين تطول غيبتها فيُعاد بناؤها بناءً بارداً، ولا موضعَ محفوظاً يُعاد
   إليه.
   فيُحفظ الموضع (المسار + التمرير) عند كل تنقّل وعند كل مغادرة، ويُقرأ
   عند الإقلاع البارد. والقيدُ ستُّ ساعات: العودةُ بعد يومٍ بدايةٌ جديدة
   لا استئناف. و«الدخول» لا يُحفظ — العودةُ إليه ليست موضعاً. */
const PLACE_KEY = "sp:last-place";
// ‏D534: الاستئنافُ لإعادة التحميل وحدها — فتحُ التطبيق بعدها يبدأ بصفحة البداية
// المختارة في الإعدادات. كانت ستُّ ساعاتٍ فتغلب صفحةُ البداية دائماً.
const PLACE_TTL = 5 * 60 * 1000;

function readPlace(): { path: string; y: number } | null {
  try {
    const raw = localStorage.getItem(PLACE_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (!p?.path || typeof p.at !== "number") return null;
    if (Date.now() - p.at > PLACE_TTL) return null;
    if (p.path === "/" || p.path.startsWith("/login")) return null;
    return { path: p.path, y: Number(p.y) || 0 };
  } catch { return null; }
}

function PlaceKeeper() {
  const loc = useLocation();
  useEffect(() => {
    const save = () => {
      const path = loc.pathname + loc.search;
      if (path === "/" || path.startsWith("/login")) return;
      try {
        localStorage.setItem(PLACE_KEY, JSON.stringify({
          path, y: window.scrollY || 0, at: Date.now(),
        }));
      } catch { /* التخزين قد يكون محجوباً — الحفظ رفاهية لا شرط */ }
    };
    save();
    // المغادرة إلى رابطٍ خارجيّ لا تمرّ بتنقّلٍ داخليّ، فيُلتقط التمرير
    // عند إخفاء الصفحة أيضاً.
    const onHide = () => { if (document.visibilityState === "hidden") save(); };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", save);
    return () => {
      save();
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", save);
    };
  }, [loc.pathname, loc.search]);
  return null;
}

function StartRedirect() {
  const { startPage } = useAppStore();
  const [ready, setReady] = useState(layoutLoaded);
  const place = React.useRef(readPlace()).current;
  useEffect(() => {
    if (layoutLoaded) return;
    const t = setInterval(() => { if (layoutLoaded) { clearInterval(t); setReady(true); } }, 60);
    const cap = setTimeout(() => { clearInterval(t); setReady(true); }, 1500);
    return () => { clearInterval(t); clearTimeout(cap); };
  }, []);
  if (!ready) return null;
  if (place) {
    // التمرير يُستعاد بعد أوّل رسمٍ للصفحة المستأنَفة.
    setTimeout(() => window.scrollTo(0, place.y), 120);
    return <Navigate to={place.path} replace />;
  }
  return <Navigate to={"/" + (startPage || "portfolio")} replace />;
}

function App() {
  const { theme, language } = useAppStore();
  useIdleLock();  // قفل تلقائي بعد الخمول (حسب اختيار المستخدم في تبويب الأمان)

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // توحيد ترتيب القائمة عبر كل الأجهزة: نجلب التخطيط المحفوظ على الخادم مرّة
  // عند الإقلاع. إن وُجد نطبّقه (يغلب على النسخة المحلية لكل متصفح). وإن كان
  // الخادم فارغاً بعد (لم يُحفظ أي ترتيب) نبذره من ترتيب هذا الجهاز — فيصبح
  // مرجعاً تلتقطه بقية الأجهزة، دون انتظار إعادة ترتيب يدوية.
  useEffect(() => {
    settingsApi.getLayout()
      .then(r => {
        const srv = r.data?.data;
        /* الشرط كان يشترط ترتيبَ قائمةٍ محفوظاً أو شبكةَ لوحة تحكم قبل أن
           يقرأ الخادمَ أصلاً — فحفظُ صفحة البداية وحدها يُهمَل كلّه. وهذه
           حالةٌ واقعية: من يغيّر صفحة البداية لا يُعيد بالضرورة ترتيب
           القائمة. فيُقرأ التخطيط متى حمل **أيَّ** إعدادٍ ذي معنى. */
        const hasSomething = !!srv && (
          (Array.isArray(srv.pageOrder) && srv.pageOrder.length) ||
          srv.layouts || srv.startPage || srv.portfolioCols ||
          (Array.isArray(srv.hiddenPages) && srv.hiddenPages.length)
        );
        if (hasSomething) {
          useAppStore.getState().applyServerLayout(srv);
        } else {
          const s = useAppStore.getState();
          settingsApi.saveLayout({ pageOrder: s.pageOrder, hiddenPages: s.hiddenPages, startPage: s.startPage, layouts: s.layouts, activeLayout: s.activeLayout }).catch(() => {});
        }
      })
      .catch(() => {})
      .finally(() => { layoutLoaded = true; });
  }, []);

  // D616: النوافذُ والقوائمُ تتلاشى عند الإغلاق بدل الاختفاء الفوريّ
  useEffect(() => installExitMotion(), []);
  // ‏D814: الصفحاتُ الأخرى تُجلب في وقت الفراغ بعد ظهور الأولى
  useEffect(() => { const t = window.setTimeout(warmPages, 1500); return () => window.clearTimeout(t); }, []);

  useEffect(() => {
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    // lang stays "en" even in Arabic mode: Chromium renders number/date input
    // digits per the DOCUMENT language (Arabic-Indic ٠١٢ on desktop when
    // lang="ar", Latin on mobile keyboards) — pinning "en" unifies ALL digits
    // Latin across desktop/tablet/mobile, incl. التوزيع النسبي inputs.
    // RTL layout is carried by `dir`, unaffected.
    document.documentElement.lang = "en";
    // الوضع الإنجليزي: طبقة الترجمة التلقائية تغطي النصوص العربية المثبّتة
    // في المكوّنات (انظر i18n-auto.ts) وتُستعاد الأصول عند العودة للعربية.
    if (language === "en") enableAutoEnglish(); else disableAutoEnglish();
  }, [language]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PlaceKeeper />
        <Suspense fallback={<div className="page-wait" data-role="page-wait" aria-busy="true" />}>{/* الدخول وما قبل الإطار */}
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {/* قفل كامل: بلا جلسة مالك لا يُعرض أي شيء من التطبيق —
              تحويل فوري لشاشة الدخول الضبابية. */}
          <Route element={<AuthGate />}>
            <Route index element={<StartRedirect />} />
            <Route path="/dashboard"      element={<Navigate to="/portfolio" replace />} />
            <Route path="/portfolio"      element={<PortfolioPage />} />
            <Route path="/portfolio/:id"  element={<CompanyPage />} />
            <Route path="/market"         element={<MarketPage />} />
            {/* ‏D687: الرسمُ البيانيّ تبويبٌ داخل «غرفة التداول» — ورابطُه القديم يصله هناك */}
            <Route path="/chart"          element={<Navigate to="/watchlist?tab=chart" replace />} />
            {/* ‏D677: المختبرُ تبويبٌ في المحفظة، والمراقبةُ قسمٌ مكانه — والرابطُ القديم يصل المختبرَ في موضعه الجديد */}
            <Route path="/watchlist"      element={<WatchlistPage />} />
            {/* ‏D694: المختبرُ تبويبٌ في تحليل الذكاء، والحوكمةُ تبويبٌ في المحفظة — والرابطان القديمان يفتحانهما */}
            <Route path="/stars"          element={<Navigate to="/watchlist?tab=lab" replace />} />
            <Route path="/governance"      element={<Navigate to="/portfolio?tab=governance" replace />} />
            <Route path="/ai"             element={<AIPage />} />
            <Route path="/calculators"    element={<CalculatorsPage />} />
            {/* قياس الأداء حُذف: أرقامه توزّعت على مواضعها (الأهداف
                والمؤشرات). والمسار يبقى محوّلاً لا محذوفاً — قد يكون صفحة
                البداية المحفوظة أو رابطاً مفتوحاً، وحذفه شاشةٌ بيضاء بلا سبب. */}
            <Route path="/performance"    element={<Navigate to="/portfolio" replace />} />
            <Route path="/reports"        element={<ReportsPage />} />
            <Route path="/library"        element={<LibraryPage />} />
            <Route path="/notifications"  element={<NotificationsPage />} />
            <Route path="/settings"       element={<SettingsPage />} />
          </Route>
        </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
