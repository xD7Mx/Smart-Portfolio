import React, { useState, useEffect } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { settingsApi, backupApi, authApi, profileApi } from "../services/api";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import { Settings, Brain, MessageSquare, Database, Shield, Lock, Info, Globe, Activity, RefreshCw, LayoutGrid, ArrowUp, ArrowDown, Home, LogIn, LogOut, Clock, Timer, KeyRound, User, Camera, Briefcase, Trash2 } from "lucide-react";
import { AvatarImg, PRESET_AVATARS } from "../components/common/Avatar";
import CollapsibleList from "../components/common/CollapsibleList";
import { IDLE_OPTIONS, getIdleMinutes, setIdleMinutes } from "../hooks/useIdleLock";
import { useT } from "../i18n";
import { PAGES } from "../components/common/MainLayout";

const SECTIONS = [
  { id: "general",   labelKey: "set.general",  icon: Settings },
  { id: "profile",   labelKey: "set.general",  label: "الملف الشخصي", icon: User },
  { id: "customize", labelKey: "set.customize", icon: LayoutGrid },
  { id: "integrations", labelKey: "set.integrations", icon: Activity },
  { id: "language",  labelKey: "set.language", icon: Globe },
  { id: "telegram",  labelKey: "set.telegram", icon: MessageSquare },
  { id: "backup",    labelKey: "set.backup",   icon: Database },
  { id: "security",  labelKey: "set.security", icon: Lock },
  { id: "about",     labelKey: "set.about",    icon: Info },
] as const;


/* تاريخ بداية المشروع — مقام الزمن في «العائد المركّب» وحده.

   سجلّ النقد يبدأ يوم أُدخلت البيانات في التطبيق لا يوم بدأ المشروع، فتحويل
   العائد إلى «سنوي» كان يقسم على شهرٍ ويضرب في اثني عشر. وهذا الحقل يصحّح
   المقام بكتابةٍ واحدة، ولا يمسّ رقماً واحداً من أرقام المحفظة. */
function ProjectStartCard() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["project-start"],
    queryFn: () => settingsApi.projectStart().then(r => r.data?.data?.start_date ?? null),
  });
  const [val, setVal] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { setVal(data || ""); }, [data]);
  const save = useMutation({
    mutationFn: (v: string) => settingsApi.saveProjectStart(v || null).then(r => r.data),
    onSuccess: (r: any) => {
      setMsg(r?.message || "حُفظ.");
      qc.invalidateQueries({ queryKey: ["project-start"] });
      qc.invalidateQueries({ queryKey: ["portfolio-metrics"] });
      setTimeout(() => setMsg(null), 3000);
    },
  });
  return (
    <div className="card">
      <h2 className="card-title mb-1">تاريخ بداية المشروع</h2>
      <p className="text-xs text-[var(--ink-muted)] mb-3">
        منه يُحسب «العائد المركّب» سنوياً. لا يغيّر أي رقمٍ آخر في المحفظة.
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <input type="date" className="input w-auto" value={val} max={new Date().toISOString().slice(0, 10)}
          onChange={e => setVal(e.target.value)} />
        <button className="btn-primary text-xs" disabled={save.isPending} onClick={() => save.mutate(val)}>حفظ</button>
        {val && <button className="btn-ghost text-xs" onClick={() => { setVal(""); save.mutate(""); }}>مسح</button>}
        {msg && <span className="text-[11px] text-[var(--pos-ink)]">{msg}</span>}
      </div>
    </div>
  );
}

/* زمنٌ نسبي بالعربية: «منذ ٣ دقائق» / «بعد ٥ ساعات». الطابع الزمني الكامل
   يُقرأ بالحساب، والنسبي يُقرأ بالعين — وهذا سجلّ أمانٍ يُقرأ بسرعة. */
function relTime(ts: number): string {
  const d = ts * 1000 - Date.now();
  const abs = Math.abs(d), fut = d > 0;
  const mins = Math.round(abs / 60000), hrs = Math.round(abs / 3600000), days = Math.round(abs / 86400000);
  /* تصريف عربي سليم: «دقيقتين» لا «2 دقيقة»، و«٣ دقائق» لا «3 دقيقة».
     السطر يُقرأ بالعين لا بالحساب، والصياغة الركيكة تُشعر بأن الشاشة مهملة. */
  const ar = (n: number, one: string, two: string, few: string, many: string) =>
    n === 1 ? one : n === 2 ? two : n <= 10 ? `${n} ${few}` : `${n} ${many}`;
  const unit = mins < 1 ? "الآن"
    : mins < 60 ? ar(mins, "دقيقة", "دقيقتين", "دقائق", "دقيقة")
    : hrs < 24 ? ar(hrs, "ساعة", "ساعتين", "ساعات", "ساعة")
    : ar(days, "يوم", "يومين", "أيام", "يوماً");
  if (unit === "الآن") return "الآن";
  return fut ? `بعد ${unit}` : `منذ ${unit}`;
}

export default function SettingsPage() {
  const t = useT();
  const qc = useQueryClient();
  const [active, setActive] = useState("general");
  const [backupBusy, setBackupBusy] = useState<"create" | "restore" | null>(null);
  const [backupMsg, setBackupMsg] = useState<string | null>(null);
  const [ownerPassword, setOwnerPassword] = useState("");
  const [idleSel, setIdleSel] = useState<number>(getIdleMinutes());
  const [spinSessions, setSpinSessions] = useState(false);
  const [pwCur, setPwCur] = useState(""); const [pwNew, setPwNew] = useState(""); const [pwNew2, setPwNew2] = useState("");
  const [revoking, setRevoking] = useState(false);
  const [pwBusy, setPwBusy] = useState(false); const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const { isOwner, login, logout } = useAuthStore();
  const loginMutation = useMutation({
    mutationFn: () => authApi.login(ownerPassword).then(r => r.data),
    onSuccess: (r) => { login(r.data.access_token); setOwnerPassword(""); },
  });
  const restoreInputRef = React.useRef<HTMLInputElement>(null);
  const { language, setLanguage, theme, setTheme, showClock, setShowClock,
          clockSeconds, setClockSeconds, clockHour12, setClockHour12,
          pageOrder, hiddenPages, startPage, movePage, togglePage, setStartPage } = useAppStore();
  const { data: integrations = [], isFetching: intFetching } = useQuery({
    queryKey: ["settings/integrations"],
    queryFn: () => settingsApi.integrations().then(r => Array.isArray(r.data.data) ? r.data.data : []),
    refetchInterval: 120000,
  });
  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ["auth-sessions"],
    queryFn: () => authApi.sessions().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: isOwner && active === "security",
    refetchInterval: 30000,
  });
  const { data: settings } = useQuery({ queryKey: ["settings"],  queryFn: () => settingsApi.get().then(r => r.data.data) });
  const { data: aiCfg }    = useQuery({ queryKey: ["settings/ai"], queryFn: () => settingsApi.ai().then(r => r.data.data) });
  const { data: tgCfg }    = useQuery({ queryKey: ["settings/telegram"], queryFn: () => settingsApi.telegram().then(r => r.data.data) });
  const [tgBusy, setTgBusy] = useState(false);
  const [tgMsg, setTgMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // ── الملف الشخصي ──
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: () => profileApi.get().then(r => r.data.data) });
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [avatarVer, setAvatarVer] = useState(0);
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  // اختيار الشخصية/الصورة معلّق حتى الضغط على «حفظ» — لا يُطبَّق فورًا.
  const [pending, setPending] = useState<{ kind: "preset" | "file"; url: string; file?: File; id?: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const avatarRef = React.useRef<HTMLInputElement>(null);
  const nameVal = displayName ?? profile?.name ?? "";
  const hasAvatar = (profile?.has_avatar || avatarVer > 0);
  // زرّ حفظ **واحد** لكل الملف الشخصي: يحفظ ما تغيّر فعلاً (الاسم و/أو
  // الصورة) في عملية واحدة — بدل زرّ منفصل لكل حقل.
  const nameDirty = displayName !== null && displayName.trim() !== (profile?.name ?? "").trim();
  const dirty = nameDirty || !!pending;
  const saveProfile = async () => {
    if (!dirty || saving) return;
    setSaving(true); setProfileMsg("جارٍ الحفظ…");
    const done: string[] = [];
    try {
      if (nameDirty) { await profileApi.save((displayName || "").trim()); done.push("الاسم"); }
      if (pending) {
        const blob = pending.kind === "file" ? pending.file! : await (await fetch(pending.url)).blob();
        await profileApi.uploadAvatar(new File([blob], "avatar", { type: (blob as Blob).type || "image/png" }));
        setAvatarVer(v => v + 1); setPending(null); done.push("الصورة");
      }
      setProfileMsg(done.length ? `تم حفظ ${done.join(" و")}.` : null);
      qc.invalidateQueries({ queryKey: ["profile"] });
    } catch (err: any) {
      setProfileMsg(err?.response?.data?.detail || "تعذّر الحفظ.");
    } finally { setSaving(false); }
  };
  const onAvatarPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    setPending({ kind: "file", url: URL.createObjectURL(f), file: f });
    setProfileMsg("لم يُحفظ بعد");
  };
  const pickPreset = (url: string, id: string) => {
    setPending({ kind: "preset", url, id });
    setProfileMsg("لم يُحفظ بعد");
  };
  const removeAvatar = async () => {
    setProfileMsg("جارٍ حذف الصورة…");
    try { await profileApi.removeAvatar(); setPending(null); setAvatarVer(v => v + 1); setProfileMsg("حُذفت الصورة — عادت أيقونة المحفظة."); qc.invalidateQueries({ queryKey: ["profile"] }); }
    catch (err: any) { setProfileMsg(err?.response?.data?.detail || "تعذّر حذف الصورة."); }
  };
  const removeName = async () => {
    try { await profileApi.save(""); setDisplayName(""); setProfileMsg("حُذف الاسم."); qc.invalidateQueries({ queryKey: ["profile"] }); }
    catch { setProfileMsg("تعذّر حذف الاسم."); }
  };

  return (
    <div className="flex flex-col gap-4 fade-in">
      {/* Horizontal icon strip on ALL screen sizes — tap an icon, its section
          opens below with full width. (Was mobile-only + desktop sidebar;
          unified since the strip reads cleaner everywhere.) */}
      <nav className="-mx-1 px-1 flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
        {SECTIONS.map(({ id, labelKey, icon: Icon, ...rest }) => (
          <button key={id} onClick={() => setActive(id)} aria-pressed={active === id}
            /* بلا إطار — انظر تعليق تبويبات المحفظة في PortfolioPage. */
            className="flex flex-col items-center gap-1 min-w-[64px] px-2 py-2 rounded-xl text-[10px] shrink-0 transition-colors"
            style={active === id
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <Icon size={18} />
            <span className="whitespace-nowrap">{(rest as any).label || t(labelKey)}</span>
          </button>
        ))}
      </nav>

      {/* Content */}
      <div className="flex-1 space-y-5 min-w-0">
        {active === "profile" && (
          <div className="space-y-5">
            <div className="card">
              {/* بلا أيقونة كبقيّة عناوين الإعدادات الاثني عشر: كانت وحدها
                  تحملها، وهي مكرّرة أصلاً في تبويب التنقّل أعلاه. */}
              <h2 className="card-title mb-4">الملف الشخصي</h2>
              <div className="flex items-center gap-4">
                {/* الصورة الرمزية */}
                <div className="relative shrink-0">
                  <div className="w-20 h-20 rounded-full overflow-hidden panel border border-[var(--hairline)] flex items-center justify-center"
                    style={pending ? { boxShadow: "0 0 0 2px var(--chart-1)" } : undefined}>
                    {pending
                      ? <img src={pending.url} alt="" className="w-full h-full object-cover" />
                      : hasAvatar
                        ? <AvatarImg refreshKey={avatarVer} iconSize={30} />
                        : <Briefcase size={30} className="text-[var(--ink-muted)]" />}
                  </div>
                  {isOwner && (
                    <button onClick={() => avatarRef.current?.click()}
                      className="absolute -bottom-1 -end-1 w-7 h-7 rounded-full bg-[var(--brand)] hover:bg-[var(--brand)] flex items-center justify-center shadow-lg border-2"
                      style={{ borderColor: "var(--card)" }}
                      title="رفع صورة من الجهاز"><Camera size={13} color="#fff" /></button>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <label className="text-xs font-bold text-[var(--ink-muted)] mb-1.5 block">اسم العرض</label>
                  <div className="flex gap-2">
                    <input className="input flex-1" placeholder="اكتب اسمك" value={nameVal} disabled={!isOwner}
                      onChange={e => { setDisplayName(e.target.value); setProfileMsg(null); }} maxLength={40} />
                    {isOwner && (
                      <button className="btn-primary shrink-0" onClick={saveProfile} disabled={!dirty || saving}>
                        {saving ? "…" : "حفظ"}
                      </button>
                    )}
                  </div>
                  {isOwner && dirty && (
                    <div className="mt-2">
                      <button onClick={() => { setPending(null); setDisplayName(null); setProfileMsg(null); }}
                        className="text-[12px] text-[var(--ink-muted)] hover:text-[var(--ink)]">إلغاء التغييرات</button>
                    </div>
                  )}
                  {isOwner && !dirty && (
                    <div className="mt-2 flex items-center gap-4">
                      {(profile?.name || "").trim() && (
                        <button onClick={removeName} className="inline-flex items-center gap-1.5 text-[11px] text-[var(--neg-ink)] hover:text-[var(--neg-ink)]">
                          <Trash2 size={12} /> حذف الاسم
                        </button>
                      )}
                      {hasAvatar && (
                        <button onClick={removeAvatar} className="inline-flex items-center gap-1.5 text-[11px] text-[var(--neg-ink)] hover:text-[var(--neg-ink)]">
                          <Trash2 size={12} /> حذف الصورة نهائيًا
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* الشخصيات الجاهزة — داخل قائمة منسدلة، صفّ واحد قابل للتمرير أفقيًا (يناسب الجوال) */}
              {isOwner && (
                <div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--line)" }}>
                  <CollapsibleList label="اختر شخصية جاهزة">
                    <div className="flex items-center gap-2.5 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
                      {PRESET_AVATARS.map(p => {
                        const sel = pending?.kind === "preset" && pending.id === p.id;
                        return (
                          <button key={p.id} onClick={() => pickPreset(p.url, p.id)} title={p.label}
                            className={"w-14 h-14 rounded-full overflow-hidden hover:scale-105 transition-all shrink-0 " + (sel ? "border-2 border-[var(--brand)]" : "border border-[var(--hairline)] hover:border-[var(--brand)]")}>
                            <img src={p.url} alt={p.label} className="w-full h-full object-cover" />
                          </button>
                        );
                      })}
                    </div>
                  </CollapsibleList>
                </div>
              )}
              <input ref={avatarRef} type="file" accept="image/*" className="hidden" onChange={onAvatarPick} />
              {profileMsg && <p className="text-xs text-[var(--ink-muted)] mt-3">{profileMsg}</p>}
            </div>

            {/* كلمة المرور — نُقلت إلى الملف الشخصي */}
            {isOwner && (
              <div className="card">
                <label className="text-xs font-bold text-[var(--ink-muted)] flex items-center gap-2 mb-3"><KeyRound size={14} /> تغيير كلمة المرور</label>
                <div className="space-y-2 max-w-sm">
                  <input type="password" className="input" placeholder="كلمة المرور الحالية" autoComplete="current-password"
                    value={pwCur} onChange={e => { setPwCur(e.target.value); setPwMsg(null); }} />
                  <input type="password" className="input" placeholder="كلمة المرور الجديدة" autoComplete="new-password"
                    value={pwNew} onChange={e => { setPwNew(e.target.value); setPwMsg(null); }} />
                  <input type="password" className="input" placeholder="تأكيد كلمة المرور الجديدة" autoComplete="new-password"
                    value={pwNew2} onChange={e => { setPwNew2(e.target.value); setPwMsg(null); }} />
                  <button className="btn-primary w-full justify-center" disabled={pwBusy || !pwCur || !pwNew}
                    onClick={async () => {
                      if (pwNew !== pwNew2) { setPwMsg({ ok: false, text: "كلمتا المرور الجديدتان غير متطابقتين." }); return; }
                      if (pwNew.length < 4) { setPwMsg({ ok: false, text: "كلمة المرور الجديدة قصيرة جداً." }); return; }
                      setPwBusy(true); setPwMsg(null);
                      try {
                        await authApi.changePassword(pwCur, pwNew);
                        setPwMsg({ ok: true, text: "تم تغيير كلمة المرور بنجاح." });
                        setPwCur(""); setPwNew(""); setPwNew2("");
                      } catch (e: any) {
                        setPwMsg({ ok: false, text: e?.response?.data?.detail || "تعذّر التغيير — تحقّق من كلمة المرور الحالية." });
                      } finally { setPwBusy(false); }
                    }}>
                    {pwBusy ? "جارٍ الحفظ…" : "حفظ كلمة المرور"}
                  </button>
                  {pwMsg && <p className={"text-xs " + (pwMsg.ok ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>{pwMsg.text}</p>}
                </div>
              </div>
            )}

            {/* تسجيل الخروج — يخصّ حسابك أنت، فمكانه هنا لا في قسم الأمان
                حيث كان يجاور فعلاً يطرد كل الأجهزة. */}
            {isOwner && (
              <div className="card flex items-center">
                <button className="btn-exit flex items-center gap-2"
                  onClick={() => { authApi.logout().catch(() => {}).finally(logout); }}>
                  <LogOut size={14} /> تسجيل الخروج
                </button>
              </div>
            )}
          </div>
        )}

        {active === "general" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.generalTitle")}</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[[t("set.appName"), settings?.app], [t("set.version"), settings?.version], [t("set.currency"), settings?.currency]].map(([k, v]) => (
                <div key={k as string}><p className="text-xs text-[var(--ink-muted)] mb-1">{k}</p><p className="font-medium text-[var(--ink)]">{(v as string) ?? "—"}</p></div>
              ))}
            </div>
          </div>
        )}

        {active === "general" && <ProjectStartCard />}

        {active === "customize" && (
          <>
          <div className="card">
            <h2 className="card-title mb-4">المظهر (Theme)</h2>
            <div className="flex gap-3 flex-wrap">
              <button onClick={() => setTheme("dark")} className={theme === "dark" ? "btn-primary" : "btn-ghost"}>🌙 داكن</button>
              <button onClick={() => setTheme("light")} className={theme === "light" ? "btn-primary" : "btn-ghost"}>☀️ فاتح</button>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title mb-4">الساعة الرسمية</h2>
            <div className="space-y-2">
              {/* إظهار الساعة — زر مستقل */}
              <div className="flex items-center gap-3 p-2.5 rounded-xl panel">
                <Clock size={15} className={showClock ? "text-[var(--warn-ink)]" : "text-[var(--ink-muted)]"} />
                <span className={"text-sm font-semibold flex-1 " + (showClock ? "text-[var(--ink)]" : "text-[var(--ink-muted)]")}>إظهار الساعة</span>
                <button className={"switch" + (showClock ? " on" : "")} onClick={() => setShowClock(!showClock)} title={showClock ? "إخفاء" : "إظهار"} />
              </div>
              {/* إظهار الثواني — زر مستقل */}
              <div className="flex items-center gap-3 p-2.5 rounded-xl panel">
                <Timer size={15} className={clockSeconds ? "text-[var(--warn-ink)]" : "text-[var(--ink-muted)]"} />
                <span className={"text-sm font-semibold flex-1 " + (clockSeconds ? "text-[var(--ink)]" : "text-[var(--ink-muted)]")}>إظهار الثواني</span>
                <button className={"switch" + (clockSeconds ? " on" : "")} onClick={() => setClockSeconds(!clockSeconds)} title={clockSeconds ? "إخفاء" : "إظهار"} />
              </div>
              {/* نظام الوقت: ١٢ / ٢٤ ساعة */}
              <div className="flex items-center gap-3 p-2.5 rounded-xl panel">
                <span className="text-sm font-semibold flex-1 text-[var(--ink)]">نظام الوقت</span>
                <div className="flex gap-1.5">
                  <button onClick={() => setClockHour12(true)} className={clockHour12 ? "btn-primary !py-1 !px-3 !text-xs" : "btn-ghost !py-1 !px-3 !text-xs"}>12 ساعة</button>
                  <button onClick={() => setClockHour12(false)} className={!clockHour12 ? "btn-primary !py-1 !px-3 !text-xs" : "btn-ghost !py-1 !px-3 !text-xs"}>24 ساعة</button>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="card-title mb-2">ترتيب الصفحات وظهورها</h2>
            <div className="space-y-1.5">
              {pageOrder.map((id, i) => {
                const page = PAGES[id];
                if (!page) return null;
                const Icon = page.icon;
                const hidden = hiddenPages.includes(id);
                return (
                  <div key={id} className="flex items-center gap-3 p-2.5 rounded-xl panel">
                    <Icon size={15} className={hidden ? "text-[var(--ink-muted)]" : "text-[var(--ink-muted)]"} />
                    <span className={"text-sm font-semibold flex-1 " + (hidden ? "text-[var(--ink-muted)] line-through" : "text-[var(--ink)]")}>{t(page.key)}</span>
                    <button className={"p-1.5 rounded-lg transition-colors " + (startPage === id ? "text-[var(--warn-ink)]" : "text-[var(--ink-muted)] hover:text-[var(--warn-ink)]")}
                      title="اجعلها صفحة البداية" disabled={hidden}
                      onClick={() => setStartPage(id)}>
                      <Home size={14} />
                    </button>
                    {id !== "settings" && (
                      <button className={"switch" + (!hidden ? " on" : "")} onClick={() => togglePage(id)} title={hidden ? "إظهار" : "إخفاء"} />
                    )}
                    <div className="flex flex-col">
                      <button className="text-[var(--ink-muted)] hover:text-[var(--ink)] disabled:opacity-20" disabled={i === 0} onClick={() => movePage(id, -1)}><ArrowUp size={13} /></button>
                      <button className="text-[var(--ink-muted)] hover:text-[var(--ink)] disabled:opacity-20" disabled={i === pageOrder.length - 1} onClick={() => movePage(id, 1)}><ArrowDown size={13} /></button>
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-[var(--ink-muted)] mt-3">🏠 صفحة البداية الحالية: {t(PAGES[startPage]?.key ?? "nav.dashboard")}</p>
          </div>

          </>
        )}

        {active === "integrations" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.integrationsTitle")}</h2>
            <div className="space-y-2">
              {integrations.length === 0 && (
                <div className="text-[var(--ink-muted)] text-sm py-4 text-center">{t("set.checking")}</div>
              )}
              {integrations.map((it: any) => {
                const map: any = {
                  up:             { color: "var(--pos-ink)", bg: "transparent", label: t("set.statusUp") },
                  down:           { color: "var(--neg-ink)", bg: "transparent",  label: t("set.statusDown") },
                  not_configured: { color: "var(--ink-muted)", bg: "transparent", label: t("set.statusNotConfigured") },
                  disabled:       { color: "var(--ink-muted)", bg: "transparent", label: t("set.statusDisabled") },
                };
                const s = map[it.status] || map.down;
                const isUp = it.status === "up";
                return (
                  <div key={it.id} className="p-3 rounded-xl panel">
                    <div className="flex items-center gap-3">
                      <span className="relative flex h-3 w-3 shrink-0">
                        {isUp && <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{background: s.color}} />}
                        <span className="relative inline-flex rounded-full h-3 w-3" style={{background: s.color}} />
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[var(--ink)] text-sm font-semibold">{language === "ar" ? it.name_ar : it.name}</p>
                        {!isUp && it.detail && <p className="text-xs text-[var(--ink-muted)] truncate">{it.detail}</p>}
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{color: s.color, background: s.bg}}>{s.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* التحديث اليدوي أُزيل — يجري تلقائياً بجدولة آمنة (قبل الافتتاح
            وبعد الإغلاق أيام التداول) والتكرار لا يهدر الحصة لأن كل طبقات
            الذكاء تخزَّن ٢٤ ساعة. see scheduler.job_portfolio_content_refresh */}


        {active === "language" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.langTitle")}</h2>
            <p className="text-sm text-[var(--ink-muted)] mb-4">{t("set.langDesc")}</p>
            <div className="flex gap-3">
              <button onClick={() => setLanguage("ar")} className={language === "ar" ? "btn-primary" : "btn-ghost"}>{t("set.arabic")}</button>
              <button onClick={() => setLanguage("en")} className={language === "en" ? "btn-primary" : "btn-ghost"}>{t("set.english")}</button>
            </div>
          </div>
        )}

        {active === "ai" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.aiTitle")}</h2>
            <div className="space-y-3 text-sm">
              {[[t("set.provider"), aiCfg?.provider], [t("set.model"), aiCfg?.model], [t("set.temperature"), aiCfg?.temperature], [t("set.maxTokens"), aiCfg?.max_tokens]].map(([k, v]) => (
                <div key={k as string} className="flex justify-between py-2 border-b border-[var(--hairline)]">
                  <span className="text-[var(--ink-muted)]">{k}</span><span className="font-medium text-[var(--ink)]">{(v as string) ?? "—"}</span>
                </div>
              ))}
              <div className="flex justify-between py-2">
                <span className="text-[var(--ink-muted)]">{t("set.apiKey")}</span>
                <span className={aiCfg?.key_configured ? "tag-g" : "tag-r"}>{aiCfg?.key_configured ? t("set.configured") : t("set.notConfigured")}</span>
              </div>
            </div>
          </div>
        )}

        {active === "telegram" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.telegramTitle")}</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-[var(--hairline)]">
                <span className="text-[var(--ink-muted)]">{t("set.statusLabel")}</span>
                <span className={tgCfg?.enabled ? "tag-g" : "tag-n"}>{tgCfg?.enabled ? t("set.enabled") : t("set.disabled")}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--hairline)]"><span className="text-[var(--ink-muted)]">{t("set.botUsername")}</span><span className="text-[var(--ink)]">{tgCfg?.username ?? "—"}</span></div>
              {/* الرمز والمعرّف: حالةٌ لا قيمة — القناة تصمت إن غاب أحدهما
                  ولو كانت «مُفعّلة»، فالصفّان يقولان أين الخلل بالضبط. */}
              <div className="flex justify-between py-2 border-b border-[var(--hairline)]">
                <span className="text-[var(--ink-muted)]">رمز البوت</span>
                <span className={tgCfg?.token_configured ? "tag-g" : "tag-r"}>{tgCfg?.token_configured ? t("set.configured") : t("set.notConfigured")}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--hairline)]">
                <span className="text-[var(--ink-muted)]">معرّف المحادثة</span>
                <span className={tgCfg?.chat_configured ? "tag-g" : "tag-r"}>{tgCfg?.chat_configured ? t("set.configured") : t("set.notConfigured")}</span>
              </div>
              <div className="flex items-center gap-3 flex-wrap pt-1">
                <button className="btn-ghost" disabled={tgBusy || !isOwner} onClick={async () => {
                  setTgBusy(true); setTgMsg(null);
                  try {
                    const d = (await settingsApi.telegramTest()).data.data;
                    setTgMsg(d?.ok
                      ? { ok: true, text: `وصلت رسالةُ الاختبار إلى تلغرام${d.username ? ` عبر @${d.username}` : ""}.` }
                      : { ok: false, text: d?.reason || "تعذّر الاتصال." });
                  } catch (err: any) {
                    // السبب الفعلي من الخادم — لا رسالةٌ عامّة تُخفي الخطأ.
                    const detail = err?.response?.data?.detail;
                    setTgMsg({ ok: false, text: typeof detail === "string" ? detail : (err?.message || "تعذّر الاتصال.") });
                  } finally { setTgBusy(false); }
                }}>{tgBusy ? "جارٍ الاختبار…" : t("set.testConn")}</button>
                {tgMsg && <span className={"text-xs " + (tgMsg.ok ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>{tgMsg.text}</span>}
              </div>
              {!isOwner && <p className="text-xs text-[var(--ink-muted)]">الاختبار يرسل رسالةً فعلية — للمالك وحده.</p>}
            </div>
          </div>
        )}

        {active === "backup" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.backupTitle")}</h2>
            <p className="text-sm text-[var(--ink-muted)] mb-4">{t("set.backupDesc")}</p>
            {!isOwner ? (
              <p className="text-sm text-[var(--warn-ink)]">سجّل دخولك كمالك (تبويب الأمان) لتنزيل أو استعادة نسخة احتياطية — تحتوي على كامل بيانات المحفظة.</p>
            ) : (
            <div className="flex gap-3 items-center flex-wrap">
              <button className="btn-primary" disabled={backupBusy !== null} onClick={async () => {
                setBackupBusy("create"); setBackupMsg(null);
                try {
                  const res = await backupApi.download();
                  const cd = res.headers?.["content-disposition"] || "";
                  const match = /filename="?([^"]+)"?/.exec(cd);
                  const filename = match?.[1] || `smart-portfolio-backup-${Date.now()}.json`;
                  const url = URL.createObjectURL(new Blob([res.data], { type: "application/json" }));
                  const a = document.createElement("a");
                  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
                  a.remove(); URL.revokeObjectURL(url);
                  setBackupMsg(t("set.backupDone"));
                } catch (err: any) {
                  // نُظهر السبب الفعلي من الخادم بدل رسالة عامة تُخفي الخطأ.
                  let detail = err?.response?.data?.detail;
                  if (!detail && err?.response?.data instanceof Blob) {
                    try { detail = JSON.parse(await err.response.data.text())?.detail; } catch {}
                  }
                  setBackupMsg(detail ? `تعذّر التنزيل: ${detail}` : t("set.backupFailed"));
                } finally {
                  setBackupBusy(null);
                }
              }}>{backupBusy === "create" ? t("set.backupWorking") : t("set.createBackup")}</button>

              <button className="btn-ghost" disabled={backupBusy !== null} onClick={() => restoreInputRef.current?.click()}>
                {backupBusy === "restore" ? t("set.backupWorking") : t("set.restoreBackup")}
              </button>
              <input ref={restoreInputRef} type="file" accept="application/json" className="hidden" onChange={async e => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                setBackupBusy("restore"); setBackupMsg(null);
                try {
                  await backupApi.restore(file);
                  await qc.invalidateQueries();
                  setBackupMsg(t("set.restoreDone"));
                } catch (err: any) {
                  const detail = err?.response?.data?.detail;
                  setBackupMsg(detail ? `تعذّرت الاستعادة: ${detail}` : t("set.backupFailed"));
                } finally {
                  setBackupBusy(null);
                }
              }} />
            </div>
            )}
            {backupMsg && <p className="text-xs text-[var(--ink-muted)] mt-3">{backupMsg}</p>}

            {/* منطقة الخطر — فورمات كامل. نسخة أمان تُكتب تلقائياً قبل المسح،
                وملفات النسخ الاحتياطية تبقى للاستعادة لاحقاً. */}
            {isOwner && (
              <div className="mt-6 pt-4 border-t border-[var(--neg-ink)]">
                <h3 className="text-xs font-bold text-[var(--neg-ink)] mb-2">منطقة الخطر</h3>
                <p className="text-xs text-[var(--ink-muted)] mb-3 leading-relaxed">
                  إعادة ضبط المصنع تمسح كل بيانات المحفظة والإشعارات والتقارير وتعيد التطبيق لوضعه الأساسي.
                </p>
                <button className="btn-ghost text-[var(--neg-ink)] border border-[var(--neg-ink)]" disabled={backupBusy !== null}
                  onClick={async () => {
                    const word = window.prompt("لتأكيد الفورمات الكامل اكتب: فورمات");
                    if (word !== "فورمات") return;
                    setBackupBusy("create"); setBackupMsg(null);
                    try {
                      const r = await backupApi.factoryReset();
                      await qc.invalidateQueries();
                      setBackupMsg(r.data?.message || "تمت إعادة الضبط.");
                    } catch (e: any) {
                      setBackupMsg(e?.response?.data?.detail || "تعذّرت إعادة الضبط.");
                    } finally {
                      setBackupBusy(null);
                    }
                  }}>
                  إعادة ضبط المصنع
                </button>
              </div>
            )}
          </div>
        )}

        {active === "security" && (
          <div className={"card" + (isOwner ? "" : " max-w-sm")}>
            <h2 className="card-title mb-4">{t("set.securityTitle")}</h2>
            {isOwner ? (
              <div className="space-y-4">
                <p className="text-sm text-[var(--pos-ink)] flex items-center gap-2"><Lock size={15} /> أنت مسجّل دخول كمالك — لديك صلاحية التعديل الكاملة.</p>

                {/* على الكمبيوتر: القفل التلقائي وتغيير كلمة المرور جنباً إلى جنب */}
                <div className="grid md:grid-cols-2 gap-6 pt-3 border-t border-[var(--hairline)]">
                {/* القفل التلقائي بعد الخمول */}
                <div>
                  <label className="text-xs font-bold text-[var(--ink-muted)] flex items-center gap-2 mb-2"><Timer size={14} /> القفل التلقائي بعد الخمول</label>
                  <div className="grid grid-cols-2 gap-2">
                    {IDLE_OPTIONS.map(o => (
                      <button key={o.minutes} onClick={() => { setIdleMinutes(o.minutes); setIdleSel(o.minutes); }}
                        className={"text-xs font-semibold px-3 py-2 rounded-lg border transition-colors "
                          + (idleSel === o.minutes
                            ? (o.minutes === 0 ? "idle-opt-warn" : "idle-opt-on")
                            : "idle-opt")}>
                        {o.label}
                      </button>
                    ))}
                  </div>
                  <p className="text-[11px] text-[var(--ink-muted)] mt-2 leading-relaxed">
                    {idleSel === 0
                      ? "لن يُقفل الحساب تلقائياً — يبقى مفتوحاً حتى تسجّل الخروج يدوياً."
                      : `يُقفل الحساب ويُطلب الدخول تلقائياً بعد ${IDLE_OPTIONS.find(o => o.minutes === idleSel)?.label} من عدم النشاط.`}
                  </p>
                </div>

                {/* تغيير كلمة المرور نُقل إلى تبويب «الملف الشخصي». */}
                </div>

                {/* الجلسات النشطة — من يدخل تطبيقك، من أي جهاز، ومتى آخر نشاط.
                    الغرض: أن ترى بعينك ما كان مخفيّاً عنك، وتُنهي ما لا تعرفه. */}
                <div className="pt-3" style={{ borderTop: "1px solid var(--hairline)" }}>
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-xs font-bold flex items-center gap-2 flex-1" style={{ color: "var(--ink-muted)" }}><Activity size={14} /> الجلسات النشطة</label>
                    {/* الزرّ كان جامداً لا يدور: الضغط يُبطل الاستعلام ويعود
                        فوراً، فلا أثر يُرى ولا يعرف المالك أن شيئاً حدث.
                        الدوران يُربط بحالة الجلب الفعلية، ويُضمن ظهوره ولو
                        عاد الردّ في جزءٍ من الثانية. */}
                    <button className="chat-tool p-1.5 rounded-lg" title="تحديث"
                      disabled={spinSessions}
                      onClick={async () => {
                        setSpinSessions(true);
                        try { await qc.refetchQueries({ queryKey: ["auth-sessions"] }); }
                        finally { setTimeout(() => setSpinSessions(false), 450); }
                      }}>
                      <RefreshCw size={14} className={spinSessions ? "animate-spin" : undefined} />
                    </button>
                  </div>
                  {sessionsLoading ? (
                    <div className="space-y-1.5">{[...Array(2)].map((_, i) => <div key={i} className="h-12 skeleton rounded-xl" />)}</div>
                  ) : sessions.length === 0 ? (
                    <p className="text-[11px] text-[var(--ink-muted)]">لا جلسات مسجَّلة بعد — تُسجَّل عند أوّل دخول بعد هذا التحديث.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {sessions.map((sn: any) => (
                        <div key={sn.jti} className="session-row flex items-center gap-3 p-2.5 rounded-xl"
                          style={sn.current ? { border: "1px solid color-mix(in srgb, var(--brand) 45%, transparent)" } : undefined}>
                          <span className="w-2 h-2 rounded-full shrink-0"
                            style={{ background: sn.active ? "var(--pos-ink)" : "var(--hairline)" }} />
                          <div className="min-w-0 flex-1">
                            <p className="text-[13px] font-semibold truncate flex items-center gap-1.5" style={{ color: "var(--ink)" }}>
                              {sn.device}
                              {/* «هذا الجهاز»: بدونه ترى قائمةً متشابهة فلا تجرؤ على
                                  إنهاء شيء، أو تطرد نفسك بالخطأ. */}
                              {sn.current && (
                                <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded"
                                  style={{
                                    color: "var(--ink)",
                                    background: "color-mix(in srgb, var(--brand) 12%, transparent)",
                                    border: "1px solid color-mix(in srgb, var(--brand) 45%, transparent)",
                                  }}>
                                  هذا الجهاز
                                </span>
                              )}
                            </p>
                            <p className="text-[11px] truncate" style={{ color: "var(--ink-muted)" }}>
                              <span dir="ltr">{sn.ip}</span>
                              {sn.last_seen ? " · آخر نشاط " + relTime(sn.last_seen) : ""}
                              {sn.expires_at ? " · تنتهي " + relTime(sn.expires_at) : ""}
                            </p>
                          </div>
                          {sn.revoked ? (
                            <span className="text-[10px] shrink-0" style={{ color: "var(--ink-muted)" }}>مُنتهية</span>
                          ) : (
                            <button className="chat-tool p-1.5 rounded-lg shrink-0"
                              title={sn.current ? "إنهاء جلستك الحالية (ستخرج فوراً)" : "إنهاء هذه الجلسة"}
                              onClick={async () => {
                                const msg = sn.current
                                  ? "هذه جلستك الحالية — إنهاؤها يُخرجك من التطبيق فوراً. متابعة؟"
                                  : `إنهاء جلسة «${sn.device}»؟ سيُطرد هذا الجهاز فوراً.`;
                                if (!window.confirm(msg)) return;
                                try { await authApi.revokeSession(sn.jti); } catch { /* تُعرض الحالة بعد التحديث */ }
                                qc.invalidateQueries({ queryKey: ["auth-sessions"] });
                              }}><LogOut size={14} /></button>
                          )}
                        </div>
                      ))}
                      {/* الفعل الذي يحتاجه المالك عند الشكّ: يطرد الأجهزة الأخرى
                          ويبقى هو داخل التطبيق — «إنهاء الكل» يطرده معها. */}
                      {sessions.filter((x: any) => !x.revoked).length > 1 && (
                        <button className="btn-ghost w-full text-[12px] mt-1"
                          onClick={async () => {
                            if (!window.confirm("إنهاء كل الجلسات الأخرى؟ ستبقى جلستك الحالية وحدها.")) return;
                            try { await authApi.revokeOthers(); } catch { /* تُعرض الحالة بعد التحديث */ }
                            qc.invalidateQueries({ queryKey: ["auth-sessions"] });
                          }}>إنهاء كل الجلسات الأخرى</button>
                      )}
                    </div>
                  )}
                </div>

                {/* «إنهاء كل الجلسات» — فعلٌ يطال كل الأجهزة، فمكانه قسم
                    الأمان. أما «تسجيل الخروج» فيخصّ حسابك، ومكانه الطبيعي
                    قسم «الملف الشخصي». */}
                <div className="flex items-center gap-2 flex-wrap">
                  <button className="btn-warn flex items-center gap-2" disabled={revoking}
                    onClick={async () => {
                      if (!window.confirm("سيُطرد كل من هو داخل التطبيق الآن على كل الأجهزة — بما فيها جهازك. متابعة؟")) return;
                      setRevoking(true);
                      try { await authApi.revokeAll(); } catch { /* التوكن سقط فوراً — متوقّع */ }
                      logout();
                      window.location.reload();
                    }}>
                    <Shield size={14} /> {revoking ? "جارٍ الإنهاء…" : "إنهاء كل الجلسات"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-[var(--ink-muted)]">يتطلب تسجيل الدخول لمنح الصلاحيات</p>
                <input
                  className="input w-full" type="password" placeholder="كلمة مرور المالك"
                  value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && ownerPassword) loginMutation.mutate(); }}
                />
                <button className="btn-primary flex items-center gap-2" disabled={loginMutation.isPending || !ownerPassword} onClick={() => loginMutation.mutate()}>
                  <LogIn size={14} /> {loginMutation.isPending ? "جارٍ التحقق…" : "تسجيل الدخول"}
                </button>
                {loginMutation.isError && <p className="text-[var(--neg-ink)] text-xs">كلمة المرور غير صحيحة</p>}
              </div>
            )}
          </div>
        )}

        {active === "about" && (
          <div className="card">
            <h2 className="card-title mb-4">{t("set.aboutTitle")}</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-[var(--ink-muted)]">{t("set.appName")}</span><span className="text-[var(--ink)]">Smart Portfolio</span></div>
              <div className="flex justify-between"><span className="text-[var(--ink-muted)]">{t("set.version")}</span><span className="text-[var(--ink)]">1.0.0</span></div>
              <div className="flex justify-between"><span className="text-[var(--ink-muted)]">الرقم التسلسلي</span><span className="text-[var(--ink)] tracking-wider" style={{ fontFamily: "'Thmanyah Serif Display', 'Inter', sans-serif" }}>{settings?.serial ?? "—"}</span></div>
              <p className="text-xs text-[var(--ink-muted)] pt-2 border-t border-[var(--hairline)]">
                {t("set.aboutText")}
              </p>
              {/* ══ تعريفُ الأداة — موضعٌ واحد لا حاشيةٌ تحت كل شاشة ══
                  (قرارُ مجلس نِصاب — مقعد الالتزام وحماية المستثمر)
                  المالكُ يكره الحواشي تحت الشاشات، وهو محقّ: حاشيةٌ تتكرّر
                  تُقرأ مرّةً ثم تُعمى. والالتزامُ لا يُستوفى بتكرارٍ يُتجاهَل
                  بل بتعريفٍ صريحٍ في موضعه — وهو التعريفُ بالتطبيق. */}
              <p className="text-xs leading-relaxed pt-3 border-t border-[var(--hairline)]"
                style={{ color: "var(--ink-muted)" }}>
                <span className="text-[var(--ink)] font-semibold">طبيعةُ الأداة.</span>{" "}
                هذا تطبيقُ قياسٍ وتحليل: يقرأ القوائمَ المالية المنشورة ويحسب
                منها مؤشّراتٍ معروفة، ويقارن كلَّ شركةٍ بأقرانها في قطاعها.
                وما يعرضه وقائعُ محسوبةٌ من مصدرها، لا استشارةً استثمارية ولا
                توصيةً بشراءٍ أو بيع، ولا ضمانَ عائد. وقرارُ الاستثمار
                لقارئه وحده ومسؤوليتُه عليه.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
