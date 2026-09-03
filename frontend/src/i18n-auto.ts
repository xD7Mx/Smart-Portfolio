/**
 * الترجمة التلقائية للوضع الإنجليزي.
 *
 * الواجهة عربية-أولاً: مئات النصوص مكتوبة عربياً مباشرة في المكوّنات.
 * بدل تفكيك 800 موضع، تعمل هذه الطبقة على DOM المعروض: قاموس مطابقة
 * تامة (مع قواعد أنماط للنصوص الديناميكية) يُطبَّق على عقد النص وسمات
 * placeholder/title/aria-label عند اختيار English، ويُستعاد الأصل عند
 * العودة للعربية. لا يمسّ القيم ولا الحقول ولا البيانات.
 */

export const AR_EN: Record<string, string> = {
  "القيمة العادلة = متوسط تقدير المحللين · درجة السلامة = الصحة المالية":
    "Fair value = analysts' mean target · Safety score = financial health",
  // ── عام/تنقّل ──
  "المحفظة": "Portfolio",
  "المحفظة الذكية": "Smart Portfolio",
  "محفظتي": "My Portfolio",
  "السوق": "Market",
  "الرسم البياني": "Chart",
  "الحوكمة": "Governance",
  "تحليل الذكاء": "AI Analysis",
  "الحاسبات": "Calculators",
  "التقارير": "Reports",
  "الإشعارات": "Notifications",
  "الإعدادات": "Settings",
  "الرئيسي": "Main",
  "عام": "General",
  "حول": "About",
  "الأمان": "Security",
  "التخصيص": "Customization",
  "اللغة": "Language",
  "تيليجرام": "Telegram",
  "النسخ الاحتياطي": "Backup",
  "مصادر البيانات": "Data Sources",
  "الذكاء الاصطناعي": "AI",
  "لوحة التحكم": "Dashboard",
  "الحيازات": "Holdings",
  "المفكرة": "Calendar",
  "الأخبار": "News",
  "آخر الأخبار": "Latest News",
  "التنبيهات": "Alerts",
  "أسواق": "Markets",
  "تداول": "Tadawul",
  "تداول TASI": "Tadawul TASI",
  "نفط برنت": "Brent Crude",
  "دخول": "Sign in",
  "تسجيل الخروج": "Sign out",
  "كلمة المرور": "Password",
  "أدخل كلمة المرور للمتابعة": "Enter your password to continue",
  "إغلاق": "Close",
  "إلغاء": "Cancel",
  "تأكيد": "Confirm",
  "حفظ": "Save",
  "حذف": "Delete",
  "تعديل": "Edit",
  "عرض": "View",
  "إخفاء": "Hide",
  "جاري الفحص...": "Checking...",
  "جارٍ التحميل": "Loading",
  "جارٍ تحميل حالة السوق...": "Loading market status...",
  "حقوق النشر محفوظة لـ D7M ©": "© D7M — All rights reserved",

  // ── المحفظة ──
  "إجمالي الثروة": "Total Wealth",
  "إجمالي المدفوع": "Total Paid-in",
  "إجمالي ما أودعته": "Total deposited",
  "القيمة السوقية": "Market Value",
  "توزيعات الأرباح": "Dividends",
  "توزيعات مستلمة": "Dividends received",
  "السيولة المتاحة": "Available Cash",
  "السيولة النقدية": "Cash",
  "السيولة": "Liquidity",
  "إجمالي السيولة": "Total Cash",
  "عائد كلي": "Total return",
  "عائد المحفظة": "Portfolio Return",
  "أرباح غير محققة": "Unrealized P/L",
  "الأرباح غير المحققة": "Unrealized P/L",
  "الربح / الخسارة": "Profit / Loss",
  "الربح/الخسارة": "P/L",
  "إضافة شركة": "Add Company",
  "إضافة شركة جديدة": "Add New Company",
  "اسم الشركة (عربي)": "Company name (Arabic)",
  "اسم الشركة (إنجليزي)": "Company name (English)",
  "ابحث عن شركة...": "Search companies...",
  "ابحث بالرمز أو الاسم (عربي/إنجليزي)": "Search by symbol or name",
  "(غير مملوكة — عرض التحليل)": "(not held — view analysis)",
  "الشركة": "Company",
  "شركات": "companies",
  "عدد الشركات": "Companies",
  "الرمز": "Symbol",
  "السعر": "Price",
  "القطاع": "Sector",
  "الأسهم": "Shares",
  "عدد الأسهم": "Shares",
  "إجمالي الأسهم": "Total shares",
  "سعر الشراء": "Buy price",
  "متوسط التكلفة": "Avg. cost",
  "متوسط التكلفة للسهم": "Avg. cost / share",
  "إجمالي التكلفة": "Total cost",
  "آخر سعر": "Last price",
  "آخر سعر:": "Last price:",
  "القيمة": "Value",
  "النوع": "Type",
  "المبلغ": "Amount",
  "الحالة": "Status",
  "الإجراءات": "Actions",
  "إجراءات": "Actions",
  "عملية جديدة": "New Transaction",
  "شراء/بيع": "Buy/Sell",
  "سجل العمليات": "Transactions Log",
  "سجل حركة السيولة": "Cash Ledger",
  "إيداع (ضخ)": "Deposit",
  "سحب": "Withdraw",
  "المدفوع: 0": "Paid: 0",
  "تعديل الأسهم/التكلفة": "Edit shares/cost",
  "تحديث بيانات المحفظة": "Refresh portfolio data",
  "توزيع القطاعات": "Sector Allocation",
  "التوافق الشرعي": "Sharia Compliance",
  "التوافق الشرعي غير محدد": "Sharia compliance unspecified",
  "الأهداف الاستثمارية": "Investment Goals",
  "إضافة هدف": "Add Goal",
  "الهدف:": "Goal:",
  "الوصول للمليون": "Road to a Million",
  "الوصول لنقطة الصفر (استرداد رأس المال)": "Break-even (capital recovery)",
  "لاسترداد رأس المال المدفوع بالكامل.": "to fully recover paid-in capital.",
  "حتى الآن — تبقّى": "so far — remaining",
  "أسهم المنحة": "Bonus shares",
  "قيمة أسهم المنحة": "Bonus shares value",
  "أسهم إعادة الاستثمار": "Reinvested shares",
  "قيمة أسهم إعادة الاستثمار": "Reinvested shares value",
  "إعادة استثمار": "Reinvest",
  "إعادة استثمار من التصفية": "Reinvested from exits",
  "أسهم مجانية: 0.00": "Bonus shares: 0.00",
  "أنتج السهم": "This holding produced",
  "حصلت هذه السنة على": "Received this year",
  "منذ التأسيس": "Since inception",
  "مؤشر عائد السهم": "Holding Yield Meter",
  "نمو العائد": "Return Growth",
  "إجمالي النمو الرأسمالي": "Total capital growth",
  "تنبيهات المحفظة والسوق": "Portfolio & market alerts",
  "أنت مسجّل دخول كمالك — لديك صلاحية التعديل الكاملة.": "Signed in as owner — full edit permissions.",
  "أضِف شركات إلى محفظتك لتظهر هنا كأزرار سريعة.": "Add companies to your portfolio to appear here as quick buttons.",
  "أضف شركات إلى محفظتك لتظهر الرقابة الشاملة تلقائياً": "Add companies to your portfolio to enable full oversight automatically",
  "المحفظة متوازنة ✓": "Portfolio balanced ✓",
  "محفظتك:": "Your portfolio:",

  // ── السوق ──
  "متابعة حية لأخبار وبيانات السوق السعودي": "Live Saudi market news and data",
  "أخبار السوق": "Market News",
  "مفكرة السوق": "Market Calendar",
  "نبض السوق": "Market Pulse",
  "مزاج السوق": "Market Mood",
  "السوق مفتوح": "Market open",
  "مغلق (عطلة)": "Closed (holiday)",
  "السوق الموازية": "Nomu (parallel market)",
  "نوماد": "Nomu",
  "الأعلى ارتفاعاً": "Top Gainers",
  "الأعلى انخفاضاً": "Top Losers",
  "الأكثر نشاطاً": "Most Active",
  "خريطة أداء القطاعات": "Sector Performance Map",
  "أقوى القطاعات وأضعفها": "Strongest & Weakest Sectors",
  "توزيع أداء السوق اليوم": "Today's Market Breadth",
  "عرض النطاق — اتساع السوق": "Range View — Market Breadth",
  "السيولة اليومية للسوق": "Daily Market Liquidity",
  "منحنى مؤشر تاسي": "TASI Index Curve",
  "منحنى خام برنت": "Brent Crude Curve",
  "شاشات السوق": "Market Screens",
  "اختر الشاشات التي تظهر أعلى صفحة السوق.": "Choose the screens shown at the top of the Market page.",
  "لم تُحسب بيانات السوق بعد": "Market data not computed yet",
  "لم تُحسب بيانات السوق بعد — تُحدَّث تلقائياً كل ساعة": "Market data not computed yet — refreshes hourly",
  "لم تُحسب السيولة بعد — تُحدَّث مع فحص السوق": "Liquidity not computed yet — updates with the market scan",
  "تعذّر فحص السوق حالياً — حاول مجدداً بعد قليل": "Market scan unavailable right now — try again shortly",
  "لا توجد إعلانات شركات حالياً": "No company announcements right now",
  "عدد الشركات في كل شريحة تغيّر — يُظهر «شكل» اليوم بنظرة.": "Company count per change bucket — today's shape at a glance.",
  "مصدر موثّق": "Trusted source",
  "ابحث عن أي سهم بالسوق — بالرمز أو الاسم...": "Search any listed stock — by symbol or name...",
  "ابحث عن سهم (بالرمز أو الاسم)...": "Search a stock (symbol or name)...",
  "ابحث عن سهم من مربع البحث بالأعلى لعرض شارته.": "Search a stock above to display its chart.",
  "شارت شموع احترافي يعمل للأسهم السعودية والعالمية": "Professional candlestick chart for Saudi and global stocks",
  "حركة السعر": "Price Action",
  "أرقام": "Argaam",

  // ── الذكاء ──
  "مساعد المحفظة الآلي": "Automated portfolio assistant",
  "رؤية الذكاء لشركات محفظتك": "AI View of Your Holdings",
  "رأي الذكاء": "AI Opinion",
  "تقييم الأداء": "Performance Review",
  "تقييم المحفظة": "Portfolio Evaluation",
  "تحليل المخاطر": "Risk Analysis",
  "مستوى المخاطر:": "Risk level:",
  "تركّز قطاعي": "Sector concentration",
  "القيمة العادلة": "Fair Value",
  "السعر العادل": "Fair Value",
  "تحت السعر العادل ≥": "Below fair value ≥",
  "الفرق عن السعر العادل": "Gap vs Fair Value",
  "إجماع أهداف المحلّلين": "Analyst consensus target",
  "التقييم مقابل السعر العادل": "Rating vs Fair Value",
  "تقييم القيمة العادلة": "Fair Value Rating",
  "درجة السلامة": "Safety Score",
  "الفرصة": "Upside",
  "التقييم": "Rating",
  "قوية": "Strong",
  "متوسط": "Average",
  "جيد": "Good",
  "عادل": "Fair",
  "مرتفع": "Elevated",
  "تقييم مبخس": "Undervalued",
  "مبالغ فيه": "Overvalued",
  "غير متاح": "N/A",
  "لا توجد بيانات تحليل كافية بعد": "Not enough analysis data yet",
  "لا توجد بيانات حالياً — يُبنى التقرير تلقائياً عند وجود شركات في المحفظة وتفعيل مفتاح الذكاء":
    "No data yet — the report builds automatically once the portfolio has companies and an AI key is set",

  // ── الحوكمة ──
  "الرقابة الشاملة": "Full Oversight",
  "التقييم العام": "Overall Score",
  "كل قطاعات السوق":
    "All market sectors — tap a sector to view its companies with governance scores and today's change.",

  // ── الشركة ──
  "نظرة عامة": "Overview",
  "التوزيعات": "Dividends",
  "القوائم المالية": "Financials",
  "التحليل الشامل": "Full Analysis",
  "البيانات المالية": "Financial Data",
  "حصة السهم": "Per share",
  "تاريخ الإصدار:": "Issued:",
  "السنوات السابقة": "Previous years",
  "من أصل": "of",

  // ── الحاسبات ──
  "أدوات تُهمّ المستثمر — تقديرات فورية تساعدك على التخطيط": "Investor tools — instant estimates to help you plan",
  "حاسبة متوسط التكلفة": "Average Cost Calculator",
  "حاسبة الاستثمار — العائد والدخل الشهري": "Investment Calculator — return & monthly income",
  "حاسبة النمو المركّب": "Compound Growth Calculator",
  "حاسبة الوصول للهدف — كم أحتاج ضخاً شهرياً؟": "Goal Calculator — required monthly contribution",
  "إضافة عملية شراء": "Add a purchase",
  "العمولات (اختياري)": "Fees (optional)",
  "مبلغ الاستثمار": "Investment amount",
  "المبلغ الأولي": "Initial amount",
  "المبلغ المستهدف": "Target amount",
  "الإضافة الشهرية": "Monthly contribution",
  "الضخ الشهري المطلوب": "Required monthly contribution",
  "العائد السنوي المتوقع %": "Expected annual return %",
  "عائد التوزيعات السنوي %": "Annual dividend yield %",
  "عدد السنوات": "Years",
  "خلال كم سنة": "Over how many years",
  "الدخل الشهري المتوقع": "Expected monthly income",
  "الدخل السنوي (توزيعات)": "Annual income (dividends)",
  "الأرباح المتوقعة من النمو": "Expected growth profit",
  "صافي الأرباح المركّبة": "Net compounded profit",
  "القيمة النهائية": "Final value",
  "القيمة بعد 5 سنة": "Value after 5 years",
  "رأس المال الحالي": "Current capital",
  "إجمالي ما ستضخّه": "Total you will contribute",
  "تقديرات افتراضية بناءً على مدخلاتك — العوائد الفعلية تتغير مع السوق.":
    "Hypothetical estimates from your inputs — actual returns vary with the market.",
  "يفترض إعادة استثمار العوائد شهرياً بمعدل ثابت — لتقريب الصورة لا للضمان.":
    "Assumes monthly reinvestment at a constant rate — an approximation, not a guarantee.",

  // ── التقارير ──
  "أنشئ تقريراً فورياً عن محفظتك — يُحفظ في الأرشيف ويمكن تحميله كصورة.":
    "Generate an instant portfolio report — saved to the archive and downloadable as an image.",
  "إنشاء تقرير جديد": "Create New Report",
  "اختر نوع الفترة ثم اضغط لإنشاء التقرير — يحسب أرقام محفظتك الحالية ويضيف تحليلاً نصياً.":
    "Pick a period type and tap to generate — computes your current numbers and adds written analysis.",
  "أرشيف التقارير": "Reports Archive",
  "تقرير": "Report",
  "يومي": "Daily",
  "أسبوعي": "Weekly",
  "شهري": "Monthly",
  "سنوي": "Yearly",
  "أسبوع": "Week",
  "شهر": "Month",
  "سنة": "Year",
  "3 أشهر": "3 Months",
  "6 أشهر": "6 Months",
  "5 سنوات": "5 Years",
  "الفترة": "Period",
  "الفترة:": "Period:",
  "تاريخ الإنشاء": "Created",
  "تحميل صورة": "Download image",
  "تقرير أداء المحفظة الاستثمارية": "Investment Portfolio Performance Report",
  "التقرير الشامل": "Comprehensive Report",
  "أداء المحفظة": "Portfolio Performance",
  "تفاصيل المراكز": "Position Details",
  "النسبة المئوية": "Percentage",
  "التفوّق على تاسي": "Outperformance vs TASI",
  "نسبة السيولة النقدية": "Cash Ratio",
  "السابق": "Previous",
  "← الحالي": "→ Current",
  "ر.س · القياس من بداية الفترة": "SAR · measured from period start",

  // ── الإشعارات ──
  "لا توجد إشعارات جديدة": "No new notifications",
  "غير مقروءة": "Unread",

  // ── الإعدادات ──
  "الإعدادات العامة": "General Settings",
  "اسم التطبيق": "App Name",
  "الإصدار": "Version",
  "العملة": "Currency",
  "المظهر (Theme)": "Appearance (Theme)",
  "اختر المظهر — يُحفظ اختيارك تلقائياً.": "Choose a theme — saved automatically.",
  "🌙 داكن": "🌙 Dark",
  "☀️ فاتح": "☀️ Light",
  "لغة الواجهة": "Interface Language",
  "اختر لغة عرض الموقع. اتجاه الصفحة يتغيّر تلقائياً.": "Choose the display language. Page direction switches automatically.",
  "العربية": "العربية",
  "ترتيب الصفحات وظهورها": "Page Order & Visibility",
  "رتّب صفحات القائمة الجانبية بالأسهم، أخفِ ما لا تحتاجه، واختر صفحة البداية 🏠 عند فتح الموقع.":
    "Reorder sidebar pages with the arrows, hide what you don't need, and pick the start page 🏠.",
  "🏠 صفحة البداية الحالية:": "🏠 Current start page:",
  "اجعلها صفحة البداية": "Make start page",
  "تخصيص الأعمدة": "Customize Columns",
  "إعدادات الذكاء الاصطناعي": "AI Settings",
  "المزوّد": "Provider",
  "النموذج": "Model",
  "درجة الحرارة": "Temperature",
  "الحد الأقصى للرموز": "Max tokens",
  "مفتاح API": "API Key",
  "اختبار الاتصال": "Test connection",
  "بوت تيليجرام": "Telegram Bot",
  "اسم البوت": "Bot name",
  "غير مُفعّل": "Not enabled",
  "مصادر البيانات المغذّية للمحفظة": "Data sources feeding the portfolio",
  "المؤشر الأخضر يعني أن المصدر يعمل ويعرض استهلاكه اليومي، الأحمر يعني خطأ، الرمادي يعني غير مُعدّ. يُحدَّث تلقائياً كل 30 ثانية.":
    "Green = source working (with daily usage), red = error, gray = not configured. Auto-refreshes every 30 seconds.",
  "النسخ الاحتياطي والاستعادة": "Backup & Restore",
  "احمِ بيانات محفظتك بنسخ احتياطية منتظمة.": "Protect your portfolio data with regular backups.",
  "إنشاء نسخة احتياطية الآن": "Back up now",
  "استعادة نسخة احتياطية": "Restore a backup",
  "القفل التلقائي بعد الخمول": "Auto-lock after idle",
  "لن يُقفل الحساب تلقائياً — يبقى مفتوحاً حتى تسجّل الخروج يدوياً.": "No auto-lock — stays open until you sign out manually.",
  "بلا قفل مطلقاً": "Never lock",
  "دقيقة واحدة": "1 minute",
  "5 دقائق": "5 minutes",
  "15 دقيقة": "15 minutes",
  "30 دقيقة": "30 minutes",
  "ساعة": "1 hour",
  "منطقة الخطر": "Danger Zone",
  "إعادة ضبط المصنع (فورمات)": "Factory Reset",
  "الرقم التسلسلي": "Serial Number",
  "حول Smart Portfolio": "About Smart Portfolio",
  "Smart Portfolio مساعد استثماري شخصي مدعوم بالذكاء الاصطناعي. يقدّم تحليلاً ودعماً لاتخاذ القرار — وجميع القرارات الاستثمارية تبقى بيدك.":
    "Smart Portfolio is a personal AI-assisted investment companion. It provides analysis and decision support — all investment decisions remain yours.",
  "تحديث الآن": "Refresh now",

  // ── أسماء بيانات شائعة ──
  "البنوك": "Banks",
  "مصرف الراجحي": "Al Rajhi Bank",
  "الراجحي": "Al Rajhi",
  "أرامكو السعودية": "Saudi Aramco",
  "ر.س": "SAR",
  "﷼": "SAR",
};

/** قواعد الأنماط للنصوص الديناميكية (أرقام متغيّرة داخل الجملة). */
export const AR_EN_PATTERNS: [RegExp, string][] = [
  [/^السوق مفتوح — يغلق خلال (\d+) س (\d+) د$/, "Market open — closes in $1h $2m"],
  [/^السوق يفتح خلال (\d+) س (\d+) د$/, "Market opens in $1h $2m"],
  [/^مغلق \(عطلة\) — (.+)$/, "Closed (holiday)"],
  [/^(\d+)س$/, "$1h"],
  [/^(\d+) شركة$/, "$1 companies"],
  [/^(\d+) سهم$/, "$1 shares"],
  [/(\d[\d,.]*)\s*ر\.س/g, "$1 SAR"],
  [/^لم تُحسب السيولة بعد/, "Liquidity not computed yet — updates with the market scan"],
  [/^آخر تحديث (.+)$/, "Last updated $1"],
  [/^آخر إغلاق متاح — (.+)$/, "Last available close — $1"],
  [/^آخر بيانات متاحة — (.+)$/, "Last available data — $1"],
  [/^تحليل (.+)$/, "Analysis — $1"],
  [/^تقرير (.+)$/, "Report $1"],
];

const saved = new WeakMap<Node, string>();
const savedAttr = new WeakMap<Element, Record<string, string>>();
let observer: MutationObserver | null = null;
let applying = false;

function translateString(t: string): string | null {
  const k = t.replace(/\s+/g, " ").trim();
  if (!k || !/[؀-ۿ]/.test(k)) return null;
  if (AR_EN[k]) return AR_EN[k];
  for (const [re, rep] of AR_EN_PATTERNS) {
    if (re.test(k)) return k.replace(re, rep);
  }
  return null;
}

function walk(root: Node) {
  // TreeWalker لا يُرجِع الجذر نفسه — لو أُضيفت عقدة نص مباشرة تُعالج هنا
  if (root.nodeType === Node.TEXT_NODE) {
    const tr = translateString(root.textContent || "");
    if (tr != null && tr !== root.textContent) {
      if (!saved.has(root)) saved.set(root, root.textContent || "");
      root.textContent = tr;
    }
    return;
  }
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let n: Node | null;
  while ((n = tw.nextNode())) {
    const tr = translateString(n.textContent || "");
    if (tr != null && tr !== n.textContent) {
      if (!saved.has(n)) saved.set(n, n.textContent || "");
      n.textContent = tr;
    }
  }
  const attrs = ["placeholder", "title", "aria-label"];
  const els = root instanceof Element ? [root, ...root.querySelectorAll("[placeholder],[title],[aria-label]")] : [...(root as Document | DocumentFragment).querySelectorAll?.("[placeholder],[title],[aria-label]") ?? []];
  for (const el of els) {
    for (const a of attrs) {
      const v = el.getAttribute?.(a);
      if (!v) continue;
      const tr = translateString(v);
      if (tr != null && tr !== v) {
        const rec = savedAttr.get(el) || {};
        if (!(a in rec)) { rec[a] = v; savedAttr.set(el, rec); }
        el.setAttribute(a, tr);
      }
    }
  }
}

export function enableAutoEnglish() {
  if (observer) return;
  applying = true; walk(document.body); applying = false;
  observer = new MutationObserver(muts => {
    if (applying) return;
    applying = true;
    for (const m of muts) {
      if (m.type === "characterData" && m.target) {
        const tr = translateString(m.target.textContent || "");
        if (tr != null && tr !== m.target.textContent) {
          if (!saved.has(m.target)) saved.set(m.target, m.target.textContent || "");
          m.target.textContent = tr;
        }
      }
      m.addedNodes?.forEach(n => walk(n));
    }
    applying = false;
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}

export function disableAutoEnglish() {
  observer?.disconnect(); observer = null;
  // استعادة الأصل العربي للعقد التي ما زالت حية
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n: Node | null;
  while ((n = tw.nextNode())) {
    const orig = saved.get(n);
    if (orig != null) n.textContent = orig;
  }
  document.querySelectorAll("[placeholder],[title],[aria-label]").forEach(el => {
    const rec = savedAttr.get(el);
    if (rec) for (const a of Object.keys(rec)) el.setAttribute(a, rec[a]);
  });
}