/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          900: "#1e3a8a",
        },
        profit:  { DEFAULT: "#22c55e", dark: "#16a34a" },
        loss:    { DEFAULT: "#ef4444", dark: "#dc2626" },
        warning: { DEFAULT: "#f59e0b", dark: "#d97706" },
        surface: {
          light: "#ffffff",
          dark:  "#0f172a",
        },
        panel: {
          light: "#f8fafc",
          dark:  "#1e293b",
        },
      },
      // استدارةُ الإطارات: `rounded-xl` هي إطارُ البطاقات في ٤٦ موضعاً، وكانت
      // ١٢px بينما مربّع البحث ١٦px — فبانت البطاقات أحدَّ منه. ورفعُها هنا
      // يصحّح المصدر نفسه؛ أمّا قاعدةُ CSS في globals فكانت تخسر الترتيب أمام
      // طبقة utilities مهما ضُبطت، فالتصحيح في السلّم لا فوقه.
      borderRadius: { xl: "14px" },
      fontFamily: {
        sans: ["Thmanyah Serif Display", "Inter", "system-ui", "sans-serif"],
        arabic: ["Thmanyah Serif Display", "sans-serif"],
        // `mono` أُزيل عن قصد: كان يشير إلى JetBrains Mono وهو **غير محمَّل في
        // التطبيق إطلاقاً** (لا @font-face له ولا ملف)، فكان كل `font-mono`
        // يسقط إلى monospace الافتراضي في المتصفح — خطّ Courier غريب تماماً عن
        // Thmanyah Serif Display. فكانت الأسعار والأرقام المالية في ٣٤ موضعاً
        // تُعرض بخطٍّ لا ينتمي للتصميم. استُبدلت كلها بـ tabular-nums التي
        // تحقّق الغرض الحقيقي (اصطفاف الأرقام عمودياً) بخطّ الموقع نفسه.
        // وحذف المفتاح يجعل أي `font-mono` جديد خطأً ظاهراً لا سقوطاً صامتاً.
      },
    },
  },
  plugins: [],
};
