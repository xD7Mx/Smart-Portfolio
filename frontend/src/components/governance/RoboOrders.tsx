/* ══ أوامرُ المستشار الآليّ ══ (‏D750 · بأمر المالك 2026-11-16 — على منهج «سندباد»)
   كلُّ «اشترِ» و«خفّف» أمرٌ بعدد أسهمه ومبلغه وسعره، بثقته رقماً، وبوّاباتِه ظاهرةً (القناعة · سيولة السهم · حجم الأمر · حدّ السهم · حدّ القطاع)؛
   ينتظر اعتمادَك كما يعتمد مديرُ المحفظة كلَّ توصيةٍ قبل تنفيذها، ويُكتشف تنفيذُه من تغيّر مركزك، وللمستشار إيقافٌ واستئناف،
   وسجلُّ دقّته يُقاس بعد شهرٍ من كلّ أمرٍ مقابل تاسي. والتطبيقُ لا ينفّذ صفقة — التنفيذُ في منصّة الوساطة. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X, Pause, Play, RefreshCw, ShieldCheck } from "lucide-react";
import { aiApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";

type Chk = { k: string; ok: boolean; d?: string };
type Order = { id: string; symbol: string; name: string; side: "شراء" | "بيع"; shares: number; price: number; amount: number;
  confidence: number | null; why: string; checks: Chk[]; status: string; created?: string; why_closed?: string };

const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;
const STATUS: Record<string, [string, string]> = {
  pending: ["بانتظار اعتمادك", "var(--brand-ink)"], approved: ["معتمد — نفّذه في منصّتك", "var(--pos-ink)"],
  executed: ["نُفّذ", "var(--pos-ink)"], rejected: ["رفضتَه", "var(--ink-muted)"], expired: ["انتهى", "var(--ink-muted)"],
};
const n0 = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 });

export default function RoboOrders() {
  const qc = useQueryClient();
  const owner = useAuthStore((s: any) => s.isOwner);
  const { data } = useQuery({ queryKey: ["robo"], queryFn: () => aiApi.robo().then(r => r.data.data), staleTime: 60_000 });
  const set = (d: any) => qc.setQueryData(["robo"], d);
  const decide = useMutation({ mutationFn: (a: { id: string; ok: boolean }) => aiApi.roboDecide(a.id, a.ok ? "approve" : "reject"),
    onSuccess: r => set(r.data.data) });
  const pause = useMutation({ mutationFn: (p: boolean) => aiApi.roboPause(p), onSuccess: r => set(r.data.data) });
  const refresh = useMutation({ mutationFn: () => aiApi.roboRefresh(), onSuccess: r => set(r.data.data) });
  if (!data) return null;
  const L = data.limits || {};
  const rec = data.record || {};
  const orders: Order[] = data.orders || [];

  return (
    <div className="robo rounded-2xl p-3.5 space-y-3" data-role="robo" style={{ border: "1px solid var(--hairline)" }}>
      <div className="flex items-center gap-2 flex-wrap">
        <p className="text-[13px] font-bold text-[var(--ink)] flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-[var(--brand-ink)]" />أوامر المستشار
        </p>
        <span className="robo-chip" data-role="robo-state" style={{ color: data.paused ? "var(--warn-ink)" : "var(--pos-ink)",
          background: mixA(data.paused ? "var(--warn-ink)" : "var(--pos-ink)", 12) }}>{data.paused ? "موقوف" : "يعمل"}</span>
        {owner && (
          <span className="ms-auto inline-flex gap-1.5">
            <button type="button" className="btn-ghost robo-btn" onClick={() => refresh.mutate()} disabled={refresh.isPending || data.paused}
              data-role="robo-refresh" aria-label="ابنِ أوامر اليوم الآن" title="ابنِ أوامر اليوم الآن">
              <RefreshCw size={14} className={refresh.isPending ? "animate-spin" : ""} /></button>
            <button type="button" className="btn-ghost robo-btn" onClick={() => pause.mutate(!data.paused)} disabled={pause.isPending}
              data-role="robo-pause" aria-label={data.paused ? "استئناف المستشار" : "إيقاف المستشار"} title={data.paused ? "استئناف" : "إيقاف"}>
              {data.paused ? <Play size={14} /> : <Pause size={14} />}<span className="text-[12px]">{data.paused ? "استئناف" : "إيقاف"}</span></button>
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5" data-role="robo-limits">
        {[`حدّ السهم ${L.stock_max}٪`, `حدّ القطاع ${L.sector_max}٪`, `سيولة السهم ≥ ${(L.min_adv || 0) / 1e6} مليون يومياً`,
          `الأمر ≤ ${L.adv_share}٪ من تداول السهم`].map(t => <span key={t} className="robo-chip robo-lim">{t}</span>)}
        <span className="robo-chip robo-lim" data-role="robo-record">
          {rec.n >= 5 ? `دقّة المستشار: ${rec.hits} من ${rec.n} (${rec.rate}٪) بعد ${rec.measure_days} يوماً مقابل تاسي`
            : `دقّة المستشار تُقاس بعد ${rec.measure_days || 30} يوماً من أوامره${rec.n ? ` — قِيس ${rec.n}` : ""}`}
        </span>
      </div>

      {orders.length === 0 ? (
        <p className="text-[12px] text-[var(--ink-muted)]" data-role="robo-empty">
          {data.paused ? "المستشار موقوف — لا أوامر حتى تستأنفه." : "لا أمرَ اليوم — لم تكتمل شروطُ شراءٍ أو بيعٍ في أيّ مركز."}
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {orders.map((o, i) => {
            const [st, sc] = STATUS[o.status] || [o.status, "var(--ink-muted)"];
            const side = o.side === "شراء" ? "var(--pos-ink)" : "var(--warn-ink)";
            return (
              <div key={o.id} className="robo-order card-rise" style={{ animationDelay: `${i * 40}ms` }} data-role="robo-order">
                <div className="flex items-center gap-2 min-w-0">
                  <CompanyLogo symbol={o.symbol} size={28} />
                  <span className="text-[13px] font-semibold text-[var(--ink)] truncate">{o.name}</span>
                  <span className="ms-auto robo-chip" style={{ color: side, background: mixA(side, 12) }}>{o.side}</span>
                </div>
                <p className="text-[13px] mt-2 text-[var(--ink)] tabular-nums">
                  <b>{n0(o.shares)}</b> سهم × <span dir="ltr">{o.price.toFixed(2)}</span> = <b>{n0(o.amount)}</b> ريال
                  {o.confidence != null && <span className="robo-conf" style={{ color: o.confidence >= 70 ? "var(--pos-ink)" : "var(--warn-ink)" }}> · ثقة {o.confidence}٪</span>}
                </p>
                <ul className="robo-checks">
                  {(o.checks || []).map((c, j) => (
                    <li key={j} className={c.ok ? "ok" : "no"}><span aria-hidden>{c.ok ? "✓" : "✗"}</span> {c.k}{c.d ? <small> — {c.d}</small> : null}</li>
                  ))}
                </ul>
                {o.why && <p className="text-[11.5px] text-[var(--ink-muted)] leading-relaxed mt-1">{o.why}</p>}
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="robo-chip" style={{ color: sc, background: mixA(sc, 11) }} data-role="robo-status">{st}</span>
                  {owner && o.status === "pending" && (
                    <span className="ms-auto inline-flex gap-1.5">
                      <button type="button" className="btn-primary robo-btn" onClick={() => decide.mutate({ id: o.id, ok: true })} disabled={decide.isPending}
                        data-role="robo-approve"><Check size={14} /> اعتماد</button>
                      <button type="button" className="btn-ghost robo-btn" onClick={() => decide.mutate({ id: o.id, ok: false })} disabled={decide.isPending}
                        data-role="robo-reject"><X size={14} /> رفض</button>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {(data.held || []).length > 0 && (
        <details className="robo-held" data-role="robo-held">
          <summary>مؤجّلة بالبوّابات ({data.held.length})</summary>
          <ul>{data.held.map((h: any) => <li key={h.symbol}><b>{h.name}</b> — {h.why}</li>)}</ul>
        </details>
      )}
      {(data.history || []).length > 0 && (
        <details className="robo-held" data-role="robo-history">
          <summary>الأوامر السابقة ({data.history.length})</summary>
          <ul>{data.history.map((o: Order) => (
            <li key={o.id}><span className="tabular-nums" dir="ltr">{(o.created || "").slice(0, 10)}</span> · {o.side} {n0(o.shares)} {o.name} — {STATUS[o.status]?.[0] || o.status}
              {o.why_closed ? ` (${o.why_closed})` : ""}</li>
          ))}</ul>
        </details>
      )}
    </div>
  );
}
