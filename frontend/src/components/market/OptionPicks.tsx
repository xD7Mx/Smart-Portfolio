/* ══ عقودُ الخيارات طويلة الأجل بميزانية العقد ══ (‏D759 · بأمر المالك 2026-11-17)
   «خانةٌ أضع فيها قيمةَ العقد — 150 أو 100 أو 50 دولاراً — فيُخرج أفضلَ الخيارات في السوق الأمريكيّ على المسار والأخبار، عقوداً طويلةَ المدى
   لا تتآكل… صفقاتٌ أختار منها ما يناسبني مع المبرّر». المحرّكُ في الخادم (‏services/option_picks)؛ وهنا الخانةُ والصفقاتُ بمبرّراتها. */
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, Copy, Check, RefreshCw } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";

type Pick = { symbol: string; name?: string; price?: number; contract: string; type: "call" | "put"; strike: number; ask: number; cost: number;
  dte: number; expiry: string; breakeven: number; need_pct: number; need_sigma: number | null; pop: number; delta: number; iv: number; oi: number;
  spread_pct: number; trend: { state: string }; news: { impact?: string; strength?: number } | null; reasons: string[] };

const PRESETS = [50, 100, 150, 300];
const n2 = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const Num = ({ v }: { v: string }) => <bdi dir="ltr" className="tabular-nums">{v}</bdi>;
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* */ } };

export default function OptionPicks() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const [budget, setBudget] = useState<number>(() => Number(lsGet("sp_optpicks_budget")) || 100);
  const [draft, setDraft] = useState(String(budget));
  const [copied, setCopied] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["option-picks", budget],
    queryFn: () => marketApi.optionPicks(budget).then(r => r.data.data),
    refetchInterval: qq => ((qq.state.data as any)?.running?.on ? 3000 : false),
  });
  const run = useMutation({ mutationFn: (b: number) => marketApi.optionPicksRun(b), onSuccess: () => setTimeout(() => q.refetch(), 600) });
  const res = q.data?.result;
  const busy = !!q.data?.running?.on || run.isPending;
  const go = (b: number) => {
    if (!(b >= 10 && b <= 10000)) return;
    setBudget(b); setDraft(String(b)); lsSet("sp_optpicks_budget", String(b));
    if (owner) run.mutate(b);
  };
  useEffect(() => { if (copied) { const t = setTimeout(() => setCopied(null), 1500); return () => clearTimeout(t); } }, [copied]);
  const picks: Pick[] = res?.picks || [];

  return (
    <div className="op card" data-role="op">
      <form className="op-bar" onSubmit={e => { e.preventDefault(); go(Number(draft)); }}>
        <label className="op-in">
          <span className="op-lbl">قيمة العقد</span>
          <span className="op-field"><span aria-hidden>$</span>
            <input type="number" inputMode="decimal" min={10} max={10000} step={10} value={draft} onChange={e => setDraft(e.target.value)}
              aria-label="قيمة العقد بالدولار" data-role="op-budget" dir="ltr" />
          </span>
        </label>
        <span className="op-presets" role="group" aria-label="قيمٌ سريعة">
          {PRESETS.map(v => (
            <button key={v} type="button" className={"seg-btn chip" + (budget === v ? " on" : "")} onClick={() => go(v)} data-role="op-preset"><Num v={`$${v}`} /></button>
          ))}
        </span>
        {owner && (
          <button type="submit" className="btn-primary op-go" disabled={busy} data-role="op-go">
            {busy ? <RefreshCw size={15} className="rl-spin" /> : <Search size={15} />} {busy ? "يبحث" : "ابحث"}
          </button>
        )}
      </form>

      {busy && <p className="op-status" data-role="op-status" role="status">{q.data?.running?.msg || "يبحث"}…</p>}

      {!busy && !res && <p className="op-empty" data-role="op-empty">اكتب قيمة العقد ثمّ «ابحث».</p>}

      {res && (
        <>
          <p className="op-meta" data-role="op-meta">
            <Num v={`$${res.budget}`} /> للعقد · آجالٌ بين <Num v={`${res.limits?.min_dte}`} /> و<Num v={`${res.limits?.max_dte}`} /> يوماً ·
            قُرئ مسارُ <Num v={`${res.scanned}`} /> رمزاً{res.news_ok ? " وأخبارُها" : " — قراءةُ الأخبار غيرُ متوفّرة الآن"}
          </p>
          {picks.length === 0 ? (
            <p className="op-empty" data-role="op-none">لا عقدَ طويلَ الأجل سائلاً بهذه القيمة باحتمالٍ معقول.</p>
          ) : (
            <div className="op-grid">
              {picks.map((p, i) => {
                const call = p.type === "call";
                const col = call ? "var(--pos-ink)" : "var(--neg-ink)";
                return (
                  <article key={p.contract} className="op-card card-rise" style={{ animationDelay: `${i * 45}ms` }} data-role="op-pick">
                    <header className="op-head">
                      <CompanyLogo symbol={p.symbol} size={28} />
                      <span className="op-sym"><b><Num v={p.symbol} /></b>{p.name && <small>{p.name}</small>}</span>
                      <span className="op-side" style={{ color: col, background: `color-mix(in srgb, ${col} 12%, transparent)` }}>
                        {call ? "خيار شراء · Call" : "خيار بيع · Put"}
                      </span>
                    </header>
                    <p className="op-line">
                      تنفيذ <b><Num v={n2(p.strike)} /></b> · ينتهي <Num v={p.expiry} /> (<Num v={`${p.dte}`} /> يوماً) · الكلفة <b><Num v={`$${n2(p.cost)}`} /></b>
                    </p>
                    <div className="op-m">
                      <span><small>احتمال الربح</small><b style={{ color: p.pop >= 35 ? "var(--pos-ink)" : "var(--warn-ink)" }}><Num v={`${p.pop.toFixed(0)}٪`} /></b></span>
                      <span><small>نقطة التعادل</small><b><Num v={n2(p.breakeven)} /></b></span>
                      <span><small>الحركة المطلوبة</small><b><Num v={`${p.need_pct > 0 ? "+" : ""}${p.need_pct.toFixed(1)}٪`} /></b></span>
                      <span><small>الدلتا</small><b><Num v={p.delta.toFixed(2)} /></b></span>
                      <span><small>التذبذب الضمني</small><b><Num v={`${p.iv.toFixed(0)}٪`} /></b></span>
                      <span><small>الاهتمام المفتوح</small><b><Num v={p.oi.toLocaleString("en-US")} /></b></span>
                    </div>
                    <ul className="op-why">{p.reasons.map((r, j) => <li key={j}>{r}</li>)}</ul>
                    <button type="button" className="btn-ghost op-copy" data-role="op-copy" onClick={() => { navigator.clipboard?.writeText(p.contract); setCopied(p.contract); }}
                      aria-label={`نسخ رمز العقد ${p.contract}`}>
                      {copied === p.contract ? <Check size={14} /> : <Copy size={14} />} <Num v={p.contract} />
                    </button>
                  </article>
                );
              })}
            </div>
          )}
          {(res.skipped || []).length > 0 && (
            <details className="robo-held" data-role="op-skipped">
              <summary><span>استُبعد (<Num v={`${res.skipped.length}`} />)</span></summary>
              <ul>{res.skipped.map((s: any) => <li key={s.symbol}><b><Num v={s.symbol} /></b> — {s.why}</li>)}</ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}
