import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, ShieldCheck, Target, BookOpen, Loader2, Send } from "lucide-react";
import { aiApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";

/* D587 · D591 — الطيارُ الآليّ للمحفظة (بأمر المالك): مستشارٌ يرى المحفظةَ كلَّها ويحميها من قراراتها.
   رأيٌ واحد بلا مفتاح: يفكّر كمستثمرٍ بعيد المدى ويدخل بحذر مضارب — «اشترِ» قناعةٌ مكتملةُ الشروط لا هلوسة. */

const ACTION_TONE: Record<string, string> = {
  "اشترِ الآن": "var(--pos-ink)", "انتظر": "var(--brand-ink)",
  "خفّف": "var(--warn-ink)", "صفِّ جزئياً": "var(--warn-ink)", "خذ الربح": "var(--warn-ink)",
  "لا تُضِف": "var(--neg-ink)", "اخرج عند الارتداد": "var(--neg-ink)", "احتفظ": "var(--ink-muted)",
};
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;

/* D589 (بأمر المالك): مربعٌ يخاطب فيه المستشارَ بوجهة نظره — «سدافكو أفكّر بالخروج… رأسُ مالي قرض… أريد بديلاً» —
   فيردّ بما لديه: مسارُها الحقيقيّ على D7M، وكلفةُ الخروج عليه، وبدائلُ متوازنةٌ من قطاعها. */
function AutopilotChat() {
  const [msgs, setMsgs] = useState<{ role: "user" | "advisor"; text: string; alts?: any[] }[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const send = async () => {
    const text = q.trim();
    if (!text || busy) return;
    const history = msgs.map(m => ({ role: m.role === "user" ? "user" : "advisor", text: m.text }));
    setMsgs(m => [...m, { role: "user", text }]);
    setQ(""); setBusy(true);
    try {
      const r = await aiApi.askAutopilot(text, history);
      const d = r.data?.data || {};
      setMsgs(m => [...m, { role: "advisor", text: d.reply || "تعذّر الرد الآن.", alts: d.alternatives || [] }]);
    } catch {
      setMsgs(m => [...m, { role: "advisor", text: "تعذّر الرد الآن — حاول بعد قليل." }]);
    } finally { setBusy(false); }
  };
  return (
    <div className="pt-3 border-t border-[var(--hairline)] space-y-2.5">
      <p className="text-xs font-bold text-[var(--ink-muted)]">حاور المستشار بوجهة نظرك</p>
      {msgs.length > 0 && (
        <div className="space-y-2">
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-start" : "flex justify-end"}>
              <div className="max-w-[92%] rounded-xl px-3 py-2 text-[13px] leading-relaxed whitespace-pre-line"
                style={m.role === "user"
                  ? { background: "var(--surface)", color: "var(--ink)" }
                  : { background: mixA("var(--brand)", 8), border: `1px solid ${mixA("var(--brand)", 20)}`, color: "var(--ink)" }}>
                {m.text}
                {m.alts && m.alts.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[var(--hairline)] space-y-1.5">
                    {m.alts.map((a: any) => (
                      <div key={a.symbol} className="flex items-center gap-2 text-xs">
                        <CompanyLogo symbol={a.symbol} size={20} />
                        <span className="font-semibold">{a.name}</span>
                        <span className="text-[var(--ink-muted)]">جودة {a.quality ?? "—"} · الشهري {a.monthly?.state ?? "—"}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && <div className="flex justify-end"><span className="text-xs text-[var(--ink-muted)] flex items-center gap-1.5"><Loader2 size={13} className="animate-spin" /> يقرأ أرقامها ومسارها وبدائلها…</span></div>}
        </div>
      )}
      <div className="flex items-end gap-2">
        <textarea value={q} onChange={e => setQ(e.target.value)} rows={2} maxLength={800}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          aria-label="وجهة نظرك للمستشار"
          className="input flex-1 text-[13px] resize-none min-h-[44px]" />
        <button onClick={send} disabled={busy || !q.trim()} aria-label="أرسل"
          className="btn-primary !p-0 min-w-[40px] min-h-[40px] justify-center">
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}

/* ‏D609 (بأمر المالك): المستشارُ مساعدُ تداولٍ استثماريّ نحو الهدف في الموعد الذي يريده المستثمر —
   لا «متى يأتي الهدف» بل «كيف آتيه في كذا سنة»: العائدُ المطلوب، والضخُّ الشهريّ، وأين يذهب المالُ وما يُخفَّف. */
function GoalPlan() {
  const [years, setYears] = useState<number>(() => { try { return Number(localStorage.getItem("sp_goal_years")) || 4; } catch { return 4; } });
  const pick = (y: number) => { setYears(y); try { localStorage.setItem("sp_goal_years", String(y)); } catch {} };
  const { data } = useQuery({
    queryKey: ["autopilot-plan", years], staleTime: 10 * 60 * 1000, retry: 0,
    queryFn: () => aiApi.autopilotPlan(years).then(r => r.data.data),
  });
  const p = data?.plan || {};
  const n = (v: any) => typeof v === "number" ? Math.round(v).toLocaleString("en-US") : "—";
  return (
    <div className="pt-3 border-t border-[var(--hairline)] space-y-2.5">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-xs font-bold text-[var(--ink-muted)] flex items-center gap-1.5"><Target size={14} /> الهدفُ في موعدك</p>
        <div className="flex gap-1">
          {[2, 3, 4, 5, 7, 10].map(y => (
            <button key={y} onClick={() => pick(y)}
              className="min-w-[32px] min-h-[32px] rounded-lg text-[11px] font-bold border tabular-nums"
              style={years === y ? { color: "var(--brand-ink)", borderColor: "var(--brand)" } : { color: "var(--ink-muted)", borderColor: "var(--hairline)" }}>
              {y}
            </button>
          ))}
        </div>
      </div>
      {!p["العائد_المطلوب_بلا_ضخ٪"] && p["العائد_المطلوب_بلا_ضخ٪"] !== 0 ? (
        <p className="text-[13px] text-[var(--ink-muted)]">غير متوفّر</p>
      ) : (
        <>
          <p className="text-[13px] text-[var(--ink)] leading-relaxed">
            لتبلغ <b className="tabular-nums">{n(data?.target)}</b> خلال <b className="tabular-nums">{years}</b> سنوات:
            عائدٌ مركّب <b className="tabular-nums" dir="ltr">{p["العائد_المطلوب_بلا_ضخ٪"]}%</b> سنوياً بلا ضخّ — {p["الحكم"]}.
          </p>
          <div className="grid grid-cols-3 gap-2">
            <div className="kpi"><div className="kpi-lbl">عائدك الحاليّ</div><div className="kpi-val tabular-nums" dir="ltr" style={{ textAlign: "right" }}>{p["عائدك_الحالي٪"] != null ? `${p["عائدك_الحالي٪"]}%` : "—"}</div></div>
            <div className="kpi"><div className="kpi-lbl">تبلغ به</div><div className="kpi-val tabular-nums">{n(p["ما_تبلغه_بعائدك_الحالي"])}</div></div>
            <div className="kpi"><div className="kpi-lbl">ضخٌّ شهريٌّ مطلوب</div><div className="kpi-val tabular-nums" style={{ color: "var(--brand-ink)" }}>{n(p["الضخ_الشهري_المطلوب"])}</div></div>
          </div>
          {(data?.buy_now?.length > 0 || data?.trim?.length > 0) && (
            <div className="space-y-1.5">
              {data.buy_now?.length > 0 && (
                <p className="text-[12px] text-[var(--ink)]"><span className="font-bold" style={{ color: "var(--pos-ink)" }}>يذهب الضخّ إلى: </span>
                  {data.buy_now.map((x: any) => x.name || x.symbol).join("، ")}</p>
              )}
              {data.trim?.length > 0 && (
                <p className="text-[12px] text-[var(--ink)]"><span className="font-bold" style={{ color: "var(--warn-ink)" }}>يُخفَّف: </span>
                  {data.trim.map((x: any) => `${x.name || x.symbol} (${x.action})`).join("، ")}</p>
              )}
            </div>
          )}
          {data?.pack_ready && !data?.buy_now?.length && (
            <p className="text-[12px] text-[var(--ink-muted)]">لا شركةَ اكتملت قناعةُ شرائها اليوم — الضخُّ يُحفظ نقداً حتى تكتمل.</p>
          )}
        </>
      )}
    </div>
  );
}

export default function AutopilotCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["autopilot"],
    queryFn: () => aiApi.portfolioAutopilot().then(r => r.data.data),
    staleTime: 30 * 60 * 1000,
    retry: 0,
  });

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <p className="card-title flex items-center gap-1.5">
          <Briefcase size={15} className="text-[var(--brand-ink)]" /> المستشار الآلي للمحفظة
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-[var(--ink-muted)] py-6">
          <Loader2 size={14} className="animate-spin" /> يقرأ المحفظةَ كلَّها: الأهداف والتوزيع والقوائم ومستويات D7M…
        </div>
      ) : isError || !data ? (
        <p className="text-xs text-[var(--ink-muted)] py-4">تعذّر رأي المستشار الآلي الآن.</p>
      ) : (
        <div className="space-y-3">
          <div className="p-3.5 rounded-xl" style={{ background: mixA("var(--brand)", 7), border: `1px solid ${mixA("var(--brand)", 22)}` }}>
            <p className="text-sm font-bold leading-relaxed text-[var(--ink)]">{data.verdict}</p>
            {data.goal && (
              <p className="text-xs mt-2 flex items-start gap-1.5 text-[var(--ink)]">
                <Target size={13} className="mt-0.5 shrink-0 text-[var(--brand-ink)]" /><span>{data.goal}</span>
              </p>
            )}
          </div>

          {Array.isArray(data.points) && data.points.length > 0 && (
            <ul className="space-y-2 px-1">
              {data.points.map((p: any, i: number) => {
                const c = p.tone === "+" ? "var(--pos-ink)" : p.tone === "-" ? "var(--neg-ink)" : "var(--ink-muted)";
                return (
                  <li key={i} className="text-[13px] leading-relaxed flex gap-2.5 text-[var(--ink)]">
                    <span className="text-[10px] mt-1 shrink-0" style={{ color: c }}>{p.tone === "+" ? "▲" : p.tone === "-" ? "▼" : "•"}</span>
                    <span>{p.t}</span>
                  </li>
                );
              })}
            </ul>
          )}

          {(data.flags || []).length > 0 && (
            <div className="space-y-1">
              {data.flags.map((f: string, i: number) => (
                <p key={i} className="text-xs text-[var(--warn-ink)]">{f}</p>
              ))}
            </div>
          )}

          {(data.actions || []).length > 0 && (
            <div className="pt-2 border-t border-[var(--hairline)]">
              <p className="text-xs font-bold text-[var(--ink-muted)] mb-2">ماذا أفعل في كلّ شركة</p>
              <div className="space-y-2">
                {data.actions.map((a: any) => {
                  const c = ACTION_TONE[a.action] || "var(--ink-muted)";
                  return (
                    <div key={a.symbol} className="flex items-start gap-2.5">
                      <CompanyLogo symbol={a.symbol} size={24} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[13px] font-semibold text-[var(--ink)]">{a.name}</span>
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded-md" style={{ color: c, background: mixA(c, 12) }}>{a.action}</span>
                          {a.level && <span className="text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">{a.level}</span>}
                        </div>
                        {a.why && <p className="text-xs text-[var(--ink-muted)] mt-0.5 leading-relaxed">{a.why}</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {(data.protections || []).length > 0 && (
            <div className="pt-2 border-t border-[var(--hairline)]">
              <p className="text-xs font-bold text-[var(--ink-muted)] mb-2 flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-[var(--pos-ink)]" /> حمايةٌ مفعّلة
              </p>
              <ul className="space-y-1">
                {data.protections.map((b: string, i: number) => <li key={i} className="text-xs text-[var(--ink)]">• {b}</li>)}
              </ul>
            </div>
          )}

          {(data.principles || []).length > 0 && (
            <div className="pt-2 border-t border-[var(--hairline)]">
              <p className="text-xs font-bold text-[var(--ink-muted)] mb-2 flex items-center gap-1.5">
                <BookOpen size={13} className="text-[var(--chart-3)]" /> من المكتبة
              </p>
              <ul className="space-y-1.5">
                {data.principles.map((p: any, i: number) => (
                  <li key={i} className="text-xs text-[var(--ink)] leading-relaxed">
                    «{p.p}» <span className="text-[var(--ink-muted)]">— {p.book}، ص{p.page}</span>
                    {p.applies && <span className="block text-[var(--ink-muted)]">{p.applies}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <div className="mt-3"><GoalPlan />
          <AutopilotChat /></div>
    </div>
  );
}
