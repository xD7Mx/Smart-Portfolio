import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Briefcase } from "lucide-react";
import { authApi, authToken, profileApi } from "../services/api";
import { AvatarImg } from "../components/common/Avatar";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const nav = useNavigate();
  const loc = useLocation() as any;

  // شاشة القفل بأسلوب ماك: أيقونة المحفظة افتراضيًا، وصورة المستخدم إن وُجدت.
  // نقطة الملف الشخصي عامّة (بلا مصادقة) فتُقرأ قبل الدخول.
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: () => profileApi.get().then(r => r.data.data),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const name = (profile?.name || "").trim();
  const hasAvatar = !!profile?.has_avatar;
  const h = new Date().getHours();
  const greet = h < 5 ? "ليلة هانئة" : h < 12 ? "صباح الخير" : h < 17 ? "طاب يومك" : "مساء الخير";

  const mutation = useMutation({
    mutationFn: () => authApi.login(password).then(r => r.data),
    onSuccess: (r) => {
      authToken.set(r.data.access_token);
      nav(loc.state?.from || "/portfolio", { replace: true });
    },
  });

  return (
    <div className="min-h-screen relative flex items-center justify-center bg-[#060b18] px-4 overflow-hidden">
      {/* خلفية ضبابية — أشكال ملوّنة مموّهة توحي بالتطبيق خلف القفل دون كشف أي شيء */}
      <div aria-hidden className="absolute inset-0 pointer-events-none" style={{ filter: "blur(90px)", opacity: 0.5 }}>
        <div style={{ position: "absolute", top: "12%", right: "15%", width: 340, height: 340, borderRadius: "50%", background: "#2563eb55" }} />
        <div style={{ position: "absolute", bottom: "10%", left: "12%", width: 300, height: 300, borderRadius: "50%", background: "#7c3aed55" }} />
        <div style={{ position: "absolute", top: "45%", left: "40%", width: 220, height: 220, borderRadius: "50%", background: "#10b98133" }} />
      </div>
      <form
        className="login-card relative w-full max-w-sm rounded-2xl p-6 space-y-4"
        onSubmit={e => { e.preventDefault(); if (password) mutation.mutate(); }}
      >
        <div className="flex flex-col items-center gap-2.5 mb-2">
          {/* الصورة الرمزية الدائرية — كشاشة دخول ماك */}
          {/* ══ الاستدارةُ بأسلوبٍ مباشر لا بصنف ══ (بأمر المالك)
              رآه المالكُ مربّعَ الإطار مع أنّ الحاويةَ والصورةَ كلتيهما
              `rounded-full` — وهو عودُ ‏D178: قصُّ الحاوية يسقط بأسبابٍ لا
              تظهر في الشيفرة (طبقةٌ مركَّبة · محرّكُ عرضٍ لا يقصّ عبر
              `overflow`). والأسلوبُ المباشر لا يغلبه صنفٌ ولا ترتيبُ تتالٍ.
              والملفُّ الشخصيّ دائريٌّ في التطبيق كلِّه، فلا استثناءَ هنا. */}
          <div className="w-24 h-24 rounded-full overflow-hidden panel border border-[#1e2a44] flex items-center justify-center shadow-lg"
               style={{ borderRadius: "9999px" }}>
            {hasAvatar
              ? <AvatarImg iconSize={38} />
              : <Briefcase size={38} className="text-[var(--brand)]" />}
          </div>
          <h1 className="text-[var(--ink)] font-bold text-lg mt-1">
            {name ? `${greet}، ${name}` : "المحفظة الذكية"}
          </h1>
          <p className="text-[var(--ink-muted)] text-xs">أدخل كلمة المرور للمتابعة</p>
        </div>
        <input
          className="input w-full"
          type="password"
          autoFocus
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="كلمة المرور"
        />
        <button className="btn-primary w-full justify-center" disabled={mutation.isPending || !password}>
          {mutation.isPending ? "جارٍ التحقق…" : "دخول"}
        </button>
        {mutation.isError && <p className="text-[var(--neg-ink)] text-xs text-center">كلمة المرور غير صحيحة</p>}
      </form>
    </div>
  );
}
