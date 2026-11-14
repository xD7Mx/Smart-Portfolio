/* ══ إدارة السيولة — أوامرُ شراءٍ آليّة ══ (بأمر المالك 2026-11-14 · D731)

   «ما عجبني التصميم الحالي، عيد التصميم… أبغاها أوتوماتيكية: هو يعرف الشركات في الحيازات وأوزانها المستهدفة،
   ويعرف كم الرصيد… بالإمكان تخصيص بعض الأشياء، لكن أوامر الشراء يفترض أنها أوتوماتيكية».

   كانت خطّةً تُكتب باليد: قيمةُ دفعة، ونسبةٌ لكلّ شركة، وخمسةُ مربّعاتٍ تؤشَّر، ثمّ بطاقةُ أوامر بعدد دفعاتٍ يُكتب.
   فصارت تُشتقّ: الأوامرُ من حاجة كلّ شركةٍ إلى هدفها (‏allocMath.buildOrders) على الرصيد الحاضر، والتخصيصُ أربعة:
   الميزانية (كلُّ السيولة · مبلغ · دفعةٌ من N)، والسعر (آخر إغلاقٍ حتى يُكتب غيرُه)، واستبعادُ شركة، والعمولة.
   والتخصيصُ تفضيلُ جهازٍ لا بيانُ محفظة: يُحفظ هنا ولا يمسّ رقماً في الخادم. والتنفيذُ يُسجَّل من الأمر نفسِه
   في نافذة المعاملة (العددُ والسعرُ معبّآن) فيُقسَم تمويلُه آليّاً هناك (‏D730). */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Droplets, Copy, Check, RotateCcw, EyeOff, Eye, PenLine } from "lucide-react";
import { allocationApi } from "../../services/api";
import { NumInput } from "../common/UI";
import CompanyLogo from "../common/CompanyLogo";
import { buildOrders, repriceRows, priceOverride } from "../../lib/allocMath";

const n0 = (n: number | null | undefined) =>
  n == null || !isFinite(Number(n)) ? "—" : Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
const n2 = (n: number | null | undefined) =>
  n == null || !isFinite(Number(n)) ? "—" : Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

type Mode = "all" | "amount" | "tranches";
type Prefs = { mode: Mode; amount: string; n: number; fee: string; excluded: number[] };
const KEY = "sp.liq.v2";
const DEF: Prefs = { mode: "all", amount: "", n: 2, fee: "0", excluded: [] };
const loadPrefs = (): Prefs => {
  try { return { ...DEF, ...(JSON.parse(localStorage.getItem(KEY) || "{}") || {}) }; } catch { return DEF; }
};
const latin = (v: string) => v.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660))
  .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x06F0)).replace(/[٫,]/g, ".").replace(/[^\d.]/g, "");

export default function LiquidityTab({ onRecord }: {
  onRecord?: (company: { id: number; name_ar: string; symbol: string }, shares: number, price: number) => void;
}) {
  const { data: alloc, isLoading, isError } = useQuery({
    queryKey: ["allocation"],
    queryFn: () => allocationApi.get().then(r => r.data.data),
  });
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* وضعُ التصفّح الخاصّ */ } }, [prefs]);
  const set = (p: Partial<Prefs>) => setPrefs(s => ({ ...s, ...p }));
  const [prices, setPrices] = useState<Record<number, string>>({});
  const [copied, setCopied] = useState(false);

  const cash = Number(alloc?.available_cash) || 0;
  const pool = Number(alloc?.reinvestment_pool) || 0;
  const priced = useMemo(() => repriceRows<any>(alloc?.items ?? [], prices, Number(alloc?.investable) || 0),
                         [alloc, prices]);
  const excluded = useMemo(() => new Set(prefs.excluded), [prefs.excluded]);
  const amountNum = Number(prefs.amount) || 0;
  const budget = prefs.mode === "all" ? cash
    : prefs.mode === "amount" ? Math.min(cash, amountNum)
    : cash / Math.max(1, prefs.n);
  const plan = useMemo(() => buildOrders(priced.rows, { investable: priced.investable, budget,
    feePct: Number(prefs.fee) || 0, excluded }), [priced, budget, prefs.fee, excluded]);
  const byId = new Map(plan.orders.map(o => [o.company_id, o]));
  const rows = priced.rows.filter((r: any) => Number(r.target_weight) > 0);
  const active = plan.orders.filter(o => o.shares > 0);

  const copy = async () => {
    const lines = rows.map((r: any) => {
      const o = byId.get(r.company_id);
      return o && o.shares > 0 ? `شراء ${o.shares.toLocaleString("en-US")} سهم ${r.symbol} ${r.name} بسعر ${n2(o.px)} = ${n2(o.cost)}` : null;
    }).filter(Boolean);
    try { await navigator.clipboard.writeText(lines.join("\n")); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { /* لا حافظة */ }
  };
  const pxField = (r: any) => (
    <span className="inline-flex items-center gap-0.5">
      <input data-role="liq-price" className={"input tabular-nums text-center" + (r.repriced ? " alloc-px-on" : "")}
        style={{ width: 74, padding: "5px 6px" }} type="text" inputMode="decimal" lang="en" dir="ltr"
        aria-label={`سعر ${r.name}`} title={r.repriced ? `سعرٌ مكتوب · آخر إغلاق ${Number(r.last_price)}` : "آخر إغلاق — اكتب سعرَ أمرك"}
        value={prices[r.company_id] ?? (Number(r.last_price) > 0 ? String(Number(r.last_price)) : "")}
        onChange={e => setPrices(s => ({ ...s, [r.company_id]: latin(e.target.value) }))}
        onBlur={() => setPrices(s => { if (priceOverride(s[r.company_id]) != null) return s; const o = { ...s }; delete o[r.company_id]; return o; })}
        onKeyDown={e => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
      {r.repriced && (
        <button type="button" className="alloc-px-reset" title={`عودة إلى آخر إغلاق ${Number(r.last_price)}`} aria-label="عودة إلى آخر إغلاق"
          onClick={() => setPrices(s => { const o = { ...s }; delete o[r.company_id]; return o; })}><RotateCcw size={13} /></button>
      )}
    </span>
  );

  if (isLoading) return <div className="card"><div className="h-40 skeleton rounded-xl" /></div>;
  if (isError || !alloc) return <div className="card text-sm text-[var(--neg-ink)]">تعذّر جلبُ الحيازات والرصيد.</div>;

  const toggle = (id: number) => set({ excluded: excluded.has(id) ? prefs.excluded.filter(x => x !== id) : [...prefs.excluded, id] });
  const scale = Math.max(1, ...rows.map((r: any) => Math.max(Number(r.current_weight) || 0, Number(r.target_weight) || 0,
                                                          byId.get(r.company_id)?.weightAfter || 0)));

  return (
    <div className="card liq" data-role="liq">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <Droplets size={15} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">إدارة السيولة</h2>
        <div className="ms-auto flex items-center gap-2">
          {priced.count > 0 && (
            <button type="button" className="unsaved-tag alloc-px-tag" onClick={() => setPrices({})}
              title="أسعارٌ مكتوبةٌ بدل آخر إغلاق — اضغط للعودة إليه">بسعرٍ مكتوب ({priced.count}) <RotateCcw size={11} /></button>
          )}
          <button type="button" className={active.length ? "btn-primary" : "btn-ghost"} data-role="liq-copy"
            disabled={!active.length} onClick={copy} title="نسخ الأوامر" aria-label="نسخ الأوامر">
            {copied ? <Check size={15} /> : <Copy size={15} />}
          </button>
        </div>
      </div>

      {/* المحصّلةُ أوّلاً: ما في الحساب، وما يُوظَّف الآن، وما يبقى */}
      <div className="liq-stats grid grid-cols-2 md:grid-cols-4 gap-2 mb-3" data-role="liq-stats">
        {([["السيولة المتاحة", cash, "var(--ink)"], ["منها إعادة استثمار", pool, "var(--brand-ink)"],
           ["تُوظَّف الآن", plan.spent + plan.fees, "var(--pos-ink)"], ["تبقى نقداً", Math.max(0, cash - plan.spent - plan.fees), "var(--ink-muted)"]] as [string, number, string][])
          .map(([l, v, c]) => (
            <div key={l} className="liq-stat rounded-xl px-3 py-2">
              <div className="text-[10px] text-[var(--ink-muted)]">{l}</div>
              <div className="text-[15px] font-extrabold tabular-nums mt-0.5" style={{ color: c }}><span dir="ltr">{n0(v)}</span></div>
            </div>
          ))}
      </div>

      {/* التخصيص: الميزانيةُ والعمولة — وما سواهما يُحسب */}
      <div className="flex items-center gap-2 flex-wrap mb-3" data-role="liq-controls">
        <div className="seg inline-flex" role="tablist" aria-label="الميزانية">
          {([["all", "كل السيولة"], ["amount", "مبلغ"], ["tranches", "دفعات"]] as [Mode, string][]).map(([m, l]) => (
            <button key={m} type="button" role="tab" aria-selected={prefs.mode === m}
              className={"seg-btn chip" + (prefs.mode === m ? " on" : "")} onClick={() => set({ mode: m })}>{l}</button>
          ))}
        </div>
        {prefs.mode === "amount" && (
          <span className="liq-in inline-flex items-center gap-1.5">
            <NumInput className="input tabular-nums" style={{ width: 110, padding: "5px 8px" }} value={prefs.amount}
              placeholder={n0(cash)} aria-label="المبلغ" onChange={(v: string) => set({ amount: v })} />
            {amountNum > cash && <span className="text-[11px] text-[var(--warn-ink)]">أكثر من المتاح — يُكتفى بـ{n0(cash)}</span>}
          </span>
        )}
        {prefs.mode === "tranches" && (
          <span className="liq-in seg inline-flex" role="tablist" aria-label="عدد الدفعات">
            {[2, 3, 4, 5].map(k => (
              <button key={k} type="button" className={"seg-btn chip" + (prefs.n === k ? " on" : "")} onClick={() => set({ n: k })}>
                <span dir="ltr">1/{k}</span>
              </button>
            ))}
          </span>
        )}
        <label className="inline-flex items-center gap-1.5 ms-auto text-[11px] text-[var(--ink-muted)]">
          العمولة %
          <NumInput className="input tabular-nums" style={{ width: 64, padding: "5px 6px" }} value={prefs.fee}
            aria-label="العمولة %" onChange={(v: string) => set({ fee: v })} />
        </label>
      </div>

      {!rows.length ? (
        <div className="text-sm text-[var(--ink-muted)] py-6 text-center">لا أوزانَ مستهدفة بعد — حدّدها في «التوزيع النسبي».</div>
      ) : (
        <div className="space-y-2" data-role="liq-orders">
          {rows.map((r: any, i: number) => {
            const o = byId.get(r.company_id);
            const off = excluded.has(r.company_id);
            const sh = o?.shares || 0;
            const cw = Number(r.current_weight) || 0, tw = Number(r.target_weight) || 0, aw = o?.weightAfter ?? cw;
            const rq = sh > 0 && o!.px > 0 ? Math.min(sh, Math.floor((Number(r.reinvest_share) || 0) / o!.px + 1e-9)) : 0;
            return (
              <div key={r.company_id} data-role="liq-order" data-off={off ? "1" : undefined}
                className={"liq-row card-rise rounded-2xl p-3" + (off ? " liq-off" : "")}
                style={{ animationDelay: `${Math.min(i, 12) * 26}ms` }}>
                <div className="liq-grid">
                  <div className="flex items-center gap-2.5 min-w-0 liq-co">
                    <CompanyLogo symbol={r.symbol} size={30} />
                    <div className="min-w-0">
                      <div className="text-[13px] font-semibold text-[var(--ink)] truncate">{r.name}</div>
                      <div className="text-[10px] text-[var(--ink-muted)] tabular-nums"><span className="text-[var(--brand-ink)]">{r.symbol}</span></div>
                    </div>
                  </div>
                  <div className="liq-px">
                    <div className="text-[10px] text-[var(--ink-muted)] mb-0.5">السعر</div>
                    {pxField(r)}
                  </div>
                  <div className="liq-shares" data-role="liq-shares">
                    <div className="text-[10px] text-[var(--ink-muted)]">{off ? "مستبعدة" : sh > 0 ? "اشترِ" : "عند هدفها"}</div>
                    <div className="text-[17px] font-extrabold tabular-nums leading-tight"
                      style={{ color: sh > 0 && !off ? "var(--pos-ink)" : "var(--ink-muted)" }}>
                      <span dir="ltr">{off ? "—" : n0(sh)}</span>{sh > 0 && !off && <span className="text-[10px] font-normal"> سهم</span>}
                    </div>
                    {rq > 0 && !off && <div className="text-[10px] text-[var(--brand-ink)] tabular-nums">منها <span dir="ltr">{n0(rq)}</span> إعادة استثمار</div>}
                  </div>
                  <div className="liq-amt">
                    <div className="text-[10px] text-[var(--ink-muted)]">المبلغ</div>
                    <div className="text-[13px] font-bold tabular-nums text-[var(--ink)]"><span dir="ltr">{sh > 0 && !off ? n2(o!.cost) : "—"}</span></div>
                  </div>
                  <div className="liq-acts flex items-center gap-1">
                    {sh > 0 && !off && onRecord && (
                      <button type="button" className="btn-ghost liq-act" data-role="liq-record" title="سجّل التنفيذ" aria-label="سجّل التنفيذ"
                        onClick={() => onRecord({ id: r.company_id, name_ar: r.name, symbol: r.symbol }, sh, o!.px)}>
                        <PenLine size={15} />
                      </button>
                    )}
                    <button type="button" className="btn-ghost liq-act" data-role="liq-toggle"
                      title={off ? "أعدها إلى الأوامر" : "استبعدها من هذه الأوامر"} aria-label={off ? "إعادة" : "استبعاد"}
                      onClick={() => toggle(r.company_id)}>
                      {off ? <Eye size={15} /> : <EyeOff size={15} />}
                    </button>
                  </div>
                </div>
                {/* الوزنُ: الحاليُّ مملوءٌ، وبعد التنفيذ امتدادُه، والهدفُ علامة — بمقياسٍ واحدٍ للصفوف كلّها */}
                <div className="mt-2.5" data-role="liq-bar" title={`الحالي ${cw}% · بعد التنفيذ ${aw.toFixed(2)}% · الهدف ${tw}%`}>
                  <div className="flex items-center justify-between text-[10px] text-[var(--ink-muted)] mb-1">
                    <span>الحالي <b className="text-[var(--ink)] tabular-nums" dir="ltr">{cw.toFixed(1)}%</b>
                      {sh > 0 && !off && <> ← <b className="text-[var(--pos-ink)] tabular-nums" dir="ltr">{aw.toFixed(1)}%</b></>}</span>
                    <span>الهدف <b className="text-[var(--brand-ink)] tabular-nums" dir="ltr">{tw}%</b></span>
                  </div>
                  <div className="wbar relative h-2 rounded-full" style={{ background: "color-mix(in srgb, var(--ink) 8%, transparent)" }}>
                    {sh > 0 && !off && (
                      <div className="wbar-fill absolute inset-y-0 rounded-full"
                        style={{ insetInlineStart: 0, width: `${Math.min(100, aw / scale * 100)}%`, background: "color-mix(in srgb, var(--pos-ink) 40%, transparent)" }} />
                    )}
                    <div className="wbar-fill absolute inset-y-0 rounded-full"
                      style={{ insetInlineStart: 0, width: `${Math.min(100, cw / scale * 100)}%`, background: "color-mix(in srgb, var(--brand) 50%, transparent)" }} />
                    <div className="wbar-mark absolute rounded-full"
                      style={{ insetInlineStart: `calc(${Math.min(100, tw / scale * 100)}% - 1.5px)`, top: -3, bottom: -3, width: 3, background: "var(--brand-ink)" }} />
                  </div>
                </div>
              </div>
            );
          })}
          <div className="liq-total rounded-2xl px-3 py-2.5 flex items-center gap-3 flex-wrap" data-role="liq-total">
            <span className="text-[11px] font-bold text-[var(--brand-ink)]">المجموع</span>
            <span className="text-[12px] text-[var(--ink-muted)]"><b className="text-[var(--pos-ink)] tabular-nums" dir="ltr">{n0(active.reduce((a, o) => a + o.shares, 0))}</b> سهم · {active.length} أمر</span>
            {plan.fees > 0 && <span className="text-[11px] text-[var(--ink-muted)]">العمولة <b className="tabular-nums" dir="ltr">{n2(plan.fees)}</b></span>}
            <span className="ms-auto text-[15px] font-extrabold tabular-nums text-[var(--ink)]"><span dir="ltr">{n2(plan.spent + plan.fees)}</span></span>
          </div>
        </div>
      )}
    </div>
  );
}
