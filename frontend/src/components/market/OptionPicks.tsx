/* ══ عقودُ الخيارات طويلة الأجل بميزانية العقد — دفترُ توصياتٍ قائمة ══ (‏D759 · ‏D762 بأمر المالك 2026-11-18)
   «خانةٌ أضع فيها قيمةَ العقد… عقوداً طويلةَ المدى لا تتآكل… صفقاتٌ أختار منها مع المبرّر». ثمّ (‏D762): «فارقُ العرض والطلب 30 دولاراً —
   خسارةٌ مباشرة… والنتائجُ كلَّ يومٍ تختلف وهي طويلةُ المدى — لازم الاختيارُ مقنع حتى السترايك… وزرُّ النسخ ينسخ رقماً لا أعرف أين أضعه —
   بدله: فتحٌ في الرسم». فالتوصيةُ تبقى بتاريخها وربحِها أو خسارتِها منذ دخولها حتى تنكسر قاعدةُ خروجٍ مكتوبة، وبطاقتُها تقول الهدفَ الفنيّ
   ولماذا هذا التنفيذ والفارقَ بالدولار وخطّةَ الخروج، وزرّاها «فتح في الرسم» و«سلسلة العقود». المحرّكُ في الخادم (‏services/option_picks). */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, RefreshCw, LineChart, Layers, LogOut, ShoppingCart, X } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";
import OptionChain from "./OptionChain";
import OrderForm from "../saqr/OrderForm";
import { dayMonth, optionTitle, parseOption } from "../../lib/options";

type Pick = { symbol: string; name?: string; contract: string; type: "call" | "put"; strike: number; ask: number; bid: number | null; cost: number;
  dte: number; expiry: string; breakeven: number; need_pct: number; pop: number; p_touch: number; target: number; target_label: string; rr: number;
  delta: number; iv: number; oi: number; spread_pct: number; spread_usd: number; px_src?: "ask" | "snap"; quote_at?: string | null;
  opened: string; new: boolean; pl_pct: number | null; mid_now: number | null; entry_mid: number; status_why?: string;
  trend: { state: string }; reasons: string[] };
type Exit = { contract: string; symbol: string; type: string; opened: string; closed: string; status: string; status_ar: string; why: string; pl_pct: number | null };

const PRESETS = [50, 100, 150, 300];
const n2 = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const Num = ({ v }: { v: string }) => <bdi dir="ltr" className="tabular-nums">{v}</bdi>;
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* */ } };
const sg = (v: number) => (v >= 0 ? "+" : "") + v.toFixed(1);
const dm = (iso: string) => { try { return dayMonth(iso); } catch { return iso; } };

export default function OptionPicks() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const nav = useNavigate();
  const [budget, setBudget] = useState<number>(() => Number(lsGet("sp_optpicks_budget")) || 150);
  const [draft, setDraft] = useState(String(budget));
  const [chainFor, setChainFor] = useState<string | null>(null);
  /* ‏D778 (المالك): «نكتفي بعقود الخيارات، وحُطّ في البطاقة نفسِها تنفيذ — زرٌّ بعبارة شراء… يطلع لي سعرُ العرض والطلب وأحدّد الأمر» */
  const [buyFor, setBuyFor] = useState<string | null>(null);
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
  /* «فتح في الرسم»: العقدُ نفسُه في غرفة التداول — رسمُه وسعرُه الحيّ وسلسلتُه */
  const openChart = (sym: string) => { lsSet("sp_room_symbol", sym); nav("/watchlist"); };
  const picks: Pick[] = res?.picks || [];
  const exits: Exit[] = res?.exits || [];

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
            {busy ? <RefreshCw size={15} className="rl-spin" /> : <Search size={15} />} {busy ? "يراجع" : "راجع"}
          </button>
        )}
      </form>

      {busy && <p className="op-status" data-role="op-status" role="status">{q.data?.running?.msg || "يراجع"}…</p>}

      {!busy && !res && <p className="op-empty" data-role="op-empty">اكتب قيمة العقد ثمّ «راجع».</p>}

      {res && (
        <>
          <p className="op-meta" data-role="op-meta">
            <Num v={`$${res.budget}`} /> للعقد · آجالٌ بين <Num v={`${res.limits?.min_dte}`} /> و<Num v={`${res.limits?.max_dte}`} /> يوماً ·
            فارقٌ ≤ <Num v={`${res.limits?.max_spread}%`} /> · قُرئ مسارُ <Num v={`${res.scanned}`} /> رمزاً{res.news_ok ? " وأخبارُها" : " — قراءةُ الأخبار غيرُ متوفّرة الآن"}
            {res.closed && " · السوقُ الأمريكيّ مغلق: العرضُ والطلب من آخر جلسة"}
          </p>
          {picks.length === 0 ? (
            <p className="op-empty" data-role="op-none">
              {res.us_session && res.us_session.state !== "open"
                ? `السوقُ الأمريكيّ ${res.us_session.label === "عطلة" ? "في عطلة" : "مغلق"} (${res.us_session.detail}) ولا عرضَ وطلبَ حقيقيّين يُبنى عليهما — تُبنى القائمةُ عند الافتتاح (17:30 بتوقيت الرياض شتاءً) وفي المراجعة اليومية منتصفَ الجلسة.`
                : "لا عقدَ طويلَ الأجل يستوفي الشروط بهذه القيمة الآن."}
            </p>
          ) : (
            <div className="op-grid">
              {picks.map((p, i) => {
                const call = p.type === "call";
                const col = call ? "var(--pos-ink)" : "var(--neg-ink)";
                const o = parseOption(p.contract);
                return (
                  <article key={p.contract} className="op-card card-rise" style={{ animationDelay: `${i * 45}ms` }} data-role="op-pick">
                    <header className="op-head">
                      <CompanyLogo symbol={p.symbol} size={28} />
                      <span className="op-sym"><b><Num v={p.symbol} /></b>{p.name && <small>{p.name}</small>}</span>
                      <span className="op-side" style={{ color: col, background: `color-mix(in srgb, ${col} 12%, transparent)` }}>
                        {call ? "خيار شراء · Call" : "خيار بيع · Put"}
                      </span>
                    </header>
                    <p className={"op-state" + (p.new ? " new" : "")} data-role="op-state">
                      {p.new ? "توصيةٌ جديدة اليوم" : <>قائمةٌ منذ {dm(p.opened)}{p.pl_pct != null && <> · <b className={p.pl_pct >= 0 ? "pos" : "neg"}><Num v={`${sg(p.pl_pct)}%`} /></b> منذ الدخول</>} · الأطروحةُ سليمة</>}
                    </p>
                    <p className="op-line">
                      <b>{o ? optionTitle(o) : p.contract}</b> · ينتهي {dm(p.expiry)} (<Num v={`${p.dte}`} /> يوماً) · الكلفة <b><Num v={`$${n2(p.cost)}`} /></b>
                      {" "}· الفارق <Num v={`$${Math.round(p.spread_usd)}`} /> (<Num v={`${p.spread_pct.toFixed(0)}%`} />)
                      {p.px_src === "snap" && <span className="op-last" data-role="op-snap">آخر جلسة</span>}
                    </p>
                    <div className="op-m">
                      <span><small>الهدف الفنيّ</small><b><Num v={n2(p.target)} /></b></span>
                      <span><small>العائد عند الهدف</small><b style={{ color: "var(--pos-ink)" }}><Num v={`${p.rr.toFixed(1)}×`} /></b></span>
                      <span><small>احتمال الربح</small><b style={{ color: p.pop >= 35 ? "var(--pos-ink)" : "var(--warn-ink)" }}><Num v={`${p.pop.toFixed(0)}%`} /></b></span>
                      <span><small>احتمال لمس الهدف</small><b><Num v={`${p.p_touch.toFixed(0)}%`} /></b></span>
                      <span><small>نقطة التعادل</small><b><Num v={n2(p.breakeven)} /></b></span>
                      <span><small>الدلتا</small><b><Num v={p.delta.toFixed(2)} /></b></span>
                    </div>
                    <ul className="op-why">{p.reasons.map((r, j) => <li key={j}>{r}</li>)}</ul>
                    <div className="op-btns">
                      {owner && (
                        <button type="button" className={(buyFor === p.contract ? "btn-ghost" : "btn-primary") + " op-act"} aria-expanded={buyFor === p.contract}
                          onClick={() => setBuyFor(v => (v === p.contract ? null : p.contract))} data-role="op-buy">
                          {buyFor === p.contract ? <><X size={14} /> إغلاق التذكرة</> : <><ShoppingCart size={14} /> شراء</>}
                        </button>
                      )}
                      <button type="button" className="btn-ghost op-act" onClick={() => openChart(p.contract)} data-role="op-open">
                        <LineChart size={14} /> فتح في الرسم
                      </button>
                      <button type="button" className="btn-ghost op-act" onClick={() => setChainFor(p.symbol)} data-role="op-chain">
                        <Layers size={14} /> سلسلة العقود
                      </button>
                    </div>
                    {owner && (
                      <div className={"sp-addf-wrap" + (buyFor === p.contract ? " open" : "")} aria-hidden={buyFor !== p.contract} data-role="op-ticket">
                        <div>{buyFor === p.contract && <OrderForm contract={p.contract} ask={p.ask} bid={p.bid} />}</div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
          {exits.length > 0 && (
            <section className="op-exits" data-role="op-exits">
              <h4><LogOut size={14} className="inline-block align-[-2px] me-1" />إشاراتُ خروج</h4>
              <ul>
                {exits.map(x => {
                  const o = parseOption(x.contract);
                  return (
                    <li key={x.contract + x.closed} data-role="op-exit" data-status={x.status}>
                      <b>{o ? optionTitle(o) : x.contract}</b>
                      <span className={"op-xst s-" + x.status}>{x.status_ar}</span>
                      {x.pl_pct != null && <b className={x.pl_pct >= 0 ? "pos" : "neg"}><Num v={`${sg(x.pl_pct)}%`} /></b>}
                      <small>{x.why} ({dm(x.opened)} ⇐ {dm(x.closed)})</small>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
          {(res.skipped || []).length > 0 && (
            <details className="robo-held" data-role="op-skipped">
              <summary><span>لم يدخل (<Num v={`${res.skipped.length}`} />)</span></summary>
              <ul>{res.skipped.map((s: any) => <li key={s.symbol}><b><Num v={s.symbol} /></b> — {s.why}</li>)}</ul>
            </details>
          )}
        </>
      )}
      {chainFor && <OptionChain underlying={chainFor} onClose={() => setChainFor(null)} onPick={c => { setChainFor(null); openChart(c); }} />}
    </div>
  );
}
