import React, { useEffect, useState } from "react";
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
import PortfolioPage   from "./pages/PortfolioPage";
import CompanyPage     from "./pages/CompanyPage";
import MarketPage      from "./pages/MarketPage";
import ReportsPage     from "./pages/ReportsPage";
import LibraryPage     from "./pages/LibraryPage";
import NotificationsPage from "./pages/NotificationsPage";
import SettingsPage    from "./pages/SettingsPage";
import AIPage          from "./pages/AIPage";
import GovernancePage  from "./pages/GovernancePage";
import CalculatorsPage from "./pages/CalculatorsPage";
import ChartPage       from "./pages/ChartPage";
import LoginPage       from "./pages/LoginPage";

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
const PLACE_TTL = 6 * 60 * 60 * 1000;

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
            <Route path="/chart"          element={<ChartPage />} />
            <Route path="/governance"      element={<GovernancePage />} />
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
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
