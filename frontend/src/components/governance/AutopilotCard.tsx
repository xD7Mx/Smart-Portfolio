import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plane, ShieldCheck, Target, BookOpen, Loader2 } from "lucide-react";
import { aiApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";

/* D587 · D588 — الطيارُ الآليّ للمحفظة (بأمر المالك): مستشارٌ يرى المحفظةَ كلَّها ويحميها من قراراتها.
   بجانب ردّه مفتاحُ «مستثمر / مضارب» بلغة `.seg` نفسِها، ويتغيّر الردُّ بما يقتضيه كلُّ وضع. */
type Mode = "investor" | "trader";

const ACTION_TONE: Record<string, string> = {
  "اشترِ الآن": "var(--pos-ink)", "ادخل الآن": "var(--pos-ink)", "اشترِ عند الدعم": "var(--brand-ink)", "ادخل عند الدعم": "var(--brand-ink)",
  "خفّف": "var(--warn-ink)", "صفِّ جزئياً": "var(--warn-ink)", "خذ الربح": "var(--warn-ink)",
  "لا تُضِف": "var(--neg-ink)", "اخرج عند الارتداد": "var(--neg-ink)", "احتفظ": "var(--ink-muted)",
};
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;

export default function AutopilotCard() {
  const [mode, setMode] = useState<Mode>(() => {
    try { return (localStorage.getItem("sp-autopilot-mode") as Mode) || "investor"; } catch { return "investor"; }
  });
  const pick = (m: Mode) => { setMode(m); try { localStorage.setItem("sp-autopilot-mode", m); } catch { /* خاصّ */ } };
  const { data, isLoading, isError } = useQuery({
    queryKey: ["autopilot", mode],
    queryFn: () => aiApi.portfolioAutopilot(mode).then(r => r.data.data),
    staleTime: 30 * 60 * 1000,
    retry: 0,
  });

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <p className="card-title flex items-center gap-1.5">
          <Plane size={15} className="text-[var(--brand-ink)]" /> المستشار الآلي للمحفظة
        </p>
        <div className="seg inline-flex w-fit" role="group" aria-label="عين المستشار">
          {([["investor", "مستثمر"], ["trader", "مضارب"]] as [Mode, string][]).map(([k, lbl]) => (
            <button key={k} onClick={() => pick(k)} aria-pressed={mode === k} className={"seg-btn" + (mode === k ? " on" : "")}>{lbl}</button>
          ))}
        </div>
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
    </div>
  );
}
