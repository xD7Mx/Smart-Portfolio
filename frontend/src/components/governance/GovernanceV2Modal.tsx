import React from "react";
import { useQuery } from "@tanstack/react-query";
import { X, ShieldCheck } from "lucide-react";
import { portfolioApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";
import ExpertPanelBoard from "./ExpertPanelBoard";

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

  const panel: any[] = Array.isArray(data?.expert_panel) ? data.expert_panel : [];

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
            {/* الخلاصةُ أوّلاً: القرارُ ودرجةُ السلامة قبل تفصيلهما — كانا
                يقعان أسفلَ إحدى عشرةَ قراءةً فيُقرآن حاشيةً لا خلاصة. */}
            {data.evaluable !== false && data.decision?.decision && (() => {
              /* اللونُ يتبع الحكمَ الخام لا مفردةَ العرض: مفردةُ النشر قد
                 تصف الحكمَ بكلماتٍ أخرى، فيسقط اللونُ إلى الرمادي. */
              const raw = data.decision.raw || data.decision.decision;
              const col = DECISION_COLOR[raw] || "var(--ink-muted)";
              return (
              <div className="flex items-center justify-between p-2.5 rounded-xl mb-3"
                   style={{ background: `${col}14`, border: `1px solid ${col}33` }}>
                <div className="flex items-baseline gap-2">
                  <span className="text-[11px] text-[var(--ink-muted)]">خلاصة المجلس</span>
                  <span className="text-[10px] text-[var(--ink-muted)] tabular-nums">ثقة {data.confidence?.score}%</span>
                </div>
                <div className="flex items-baseline gap-3">
                  {typeof data.finance_score === "number" && (
                    <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">درجة الجودة المالية {data.finance_score}/100</span>
                  )}
                  <span className="text-sm font-bold" style={{ color: col }}>{data.decision.decision}</span>
                </div>
              </div>
              ); })()}

            {data.decision?.reason && data.evaluable !== false && (
              <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed mb-3">{data.decision.reason}</p>
            )}

            {data.confidence?.warning && (
              <div className="mb-3 p-2 rounded-lg text-[11px]" style={{ background: "transparent", color: "var(--warn-ink)" }}>
                ⚠ {data.confidence.warning}
              </div>
            )}

            <ExpertPanelBoard panel={panel} />

            {Array.isArray(data.enriched_fields) && data.enriched_fields.length > 0 && (
              <p className="text-[10px] text-[var(--ink-muted)] mb-3">حقول مُكمَّلة اشتقاقاً: {data.enriched_fields.join("، ")}</p>
            )}

            {data.evaluable === false ? (
              /* امتناع أنيق — لا حكم حيث لا تكفي البيانات. بلا نبرة آمرة. */
              <div>
                <div className="flex items-center justify-between p-2.5 rounded-xl"
                     style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
                  <span className="text-[11px] text-[var(--ink-muted)]">خلاصة المجلس</span>
                  <span className="text-sm font-medium text-[var(--ink-muted)]">—</span>
                </div>
                <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed mt-2">{data.decision?.reason || "البيانات المتاحة لا تكفي لحكم موثوق بمعايير الخبراء."}</p>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
