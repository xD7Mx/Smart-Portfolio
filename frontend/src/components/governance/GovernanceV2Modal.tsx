import React from "react";
import { useQuery } from "@tanstack/react-query";
import { X, ShieldCheck } from "lucide-react";
import { portfolioApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";

const TONE_COLOR: Record<string, string> = {
  green: "var(--pos-ink)", yellow: "var(--warn-ink)", red: "var(--neg-ink)", na: "var(--ink-muted)",
};

const DECISION_COLOR: Record<string, string> = {
  "شراء قوي": "var(--pos-ink)", "شراء": "var(--pos-ink)", "انتظار": "var(--warn-ink)", "تجنب": "var(--neg-ink)",
};

export default function GovernanceV2Modal({ symbol, name, onClose }: { symbol: string; name: string; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["governance-v2", symbol],
    queryFn: () => portfolioApi.governanceV2(symbol).then(r => r.data.data),
  });

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-box fade-in" style={{ maxWidth: 520 }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <CompanyLogo symbol={symbol} size={28} />
            <div>
              <p className="text-sm font-bold text-[var(--ink)]">{name}</p>
              <p className="text-[10px] text-[var(--ink-muted)] flex items-center gap-1"><ShieldCheck size={10} /> ميزان خبراء الحوكمة</p>
            </div>
          </div>
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            <div className="h-6 skeleton rounded-md" /><div className="h-6 skeleton rounded-md" />
            <div className="h-6 skeleton rounded-md" /><div className="h-6 skeleton rounded-md" />
          </div>
        ) : !data ? (
          <div className="py-10 text-center text-[var(--ink-muted)] text-sm">لا تتوفر قوائم مالية كافية لهذه الشركة بعد</div>
        ) : (
          <>
            {data.confidence?.warning && (
              <div className="mb-3 p-2 rounded-lg text-[11px]" style={{ background: "transparent", color: "var(--warn-ink)" }}>
                ⚠ {data.confidence.warning}
              </div>
            )}

            {Array.isArray(data.expert_panel) && data.expert_panel.length > 0 && (
              <div className="mb-3.5">
                <div className="space-y-1.5">
                  {data.expert_panel.map((e: any, i: number) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-[11px]">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: TONE_COLOR[e.tone] || "var(--ink-muted)" }} />
                        <span className="text-[var(--ink)] shrink-0">{e.expert}</span>
                        <span className="text-[var(--ink-muted)] truncate">· {e.metric} {e.reading}</span>
                      </div>
                      <span className="shrink-0 font-medium" style={{ color: TONE_COLOR[e.tone] || "var(--ink-muted)" }}>{e.verdict}</span>
                    </div>
                  ))}
                </div>
                {Array.isArray(data.enriched_fields) && data.enriched_fields.length > 0 && (
                  <p className="text-[10px] text-[var(--ink-muted)] mt-2">ℹ︎ حقول مُكمَّلة اشتقاقاً (تقدير): {data.enriched_fields.join("، ")}</p>
                )}
              </div>
            )}

            {data.evaluable === false ? (
              /* امتناع أنيق — لا حكم حيث لا تكفي البيانات. بلا نبرة آمرة. */
              <div>
                <div className="flex items-center justify-between p-2.5 rounded-xl"
                     style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
                  <span className="text-[11px] text-[var(--ink-muted)]">خلاصة المجلس</span>
                  <span className="text-sm font-medium text-[var(--ink-muted)]">بانتظار القوائم</span>
                </div>
                <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed mt-2">{data.decision?.reason || "البيانات المتاحة لا تكفي لحكم موثوق بمعايير الخبراء."}</p>
              </div>
            ) : (
              <>
                {/* القرار — خلاصة توافق المجلس (أساسي بحت). */}
                {data.decision?.decision && (
                  <div className="flex items-center justify-between p-2.5 rounded-xl"
                       style={{ background: `${DECISION_COLOR[data.decision.decision] || "var(--ink-muted)"}14`, border: `1px solid ${DECISION_COLOR[data.decision.decision] || "var(--ink-muted)"}33` }}>
                    <span className="text-[11px] text-[var(--ink-muted)]">خلاصة المجلس · ثقة {data.confidence?.score}%</span>
                    <span className="text-sm font-bold" style={{ color: DECISION_COLOR[data.decision.decision] || "var(--ink-muted)" }}>{data.decision.decision}</span>
                  </div>
                )}
              </>
            )}

          </>
        )}
      </div>
    </div>
  );
}
