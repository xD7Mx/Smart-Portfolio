/* إدارة السيولة — خطّة ضخّ رأس المال على دفعات.

   مربّعٌ واحد: قيمة الدفعة. وكل شركةٍ لها نسبةٌ منها تبدأ من وزنها **المستهدف**
   في التوزيع النسبي وتقبل التحرير، فالمبلغ = الدفعة × النسبة × عدد الدفعات
   المؤشَّرة. والحساب محليٌّ فوريّ، والحفظ بزرٍّ صريح: الخطّة تُعدَّل عشرات
   المرّات في الجلسة، فحفظ كل ضغطة يملأ الشبكة ويجعل التراجع مستحيلاً.
*/
import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Droplets, Save, RotateCcw, ClipboardList } from "lucide-react";
import { liquidityApi } from "../../services/api";
import { NumInput } from "../common/UI";
import CompanyLogo from "../common/CompanyLogo";

const fmt = (n: number | null | undefined, d = 0) =>
  n == null ? "—" : Number(n).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });

type Row = {
  company_id: number; symbol: string; name: string;
  share_pct: number; pct_is_auto: boolean; tranches: boolean[]; exec_tranches: number;
  price: number; live_price: number; price_is_override: boolean;
};

type Draft = Record<string, string>;

/* حقلٌ رقميّ محرَّر: يعرض النصّ الخام أثناء الكتابة، وإلّا فالقيمة المنسَّقة.

   ومكانه **خارج** المكوّن الأب عمداً: تعريف مكوّنٍ داخل دالة العرض يُنتج نوعاً
   جديداً مع كل ضغطة مفتاح، فيُفكّك React الحقل ويُعيد بناءه فيضيع التركيز
   ويتوقّف الكتابة فجأة — وهي العلّة نفسها التي أُصلحت في صناديق التحرير سابقاً. */
function Field({ id, field, value, width, decimals, onNum, allowDecimal = true, draft, setDraft }: {
  id: number; field: string; value: number; width: number;
  decimals?: number; allowDecimal?: boolean; onNum: (n: number) => void;
  draft: Draft; setDraft: React.Dispatch<React.SetStateAction<Draft>>;
}) {
  const key = `${id}:${field}`;
  const shown = draft[key] ?? (decimals != null ? Number(value ?? 0).toFixed(decimals) : String(value ?? ""));
  return (
    <NumInput className="input" style={{ width, padding: "5px 8px" }}
      allowDecimal={allowDecimal}
      value={shown}
      onChange={(v: string) => {
        setDraft(d => ({ ...d, [key]: v }));
        onNum(Number(v) || 0);
      }}
      onBlur={() => setDraft(d => { const n = { ...d }; delete n[key]; return n; })} />
  );
}

export default function LiquidityTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["liquidity"],
    queryFn: () => liquidityApi.get().then((r: any) => r.data.data),
    retry: 0,
  });

  const [rows, setRows] = useState<Row[]>([]);
  const [tranche, setTranche] = useState<string>("");
  /* بطاقتان مستقلّتان بزرَّي حفظ. والعَلَمان منفصلان ليعرف المالك أيّهما فيه
     تغييرٌ معلّق؛ أمّا الإرسال فيحمل الخطّة كاملةً في الحالتين — الطلب واحد،
     وإرسال نصف الخطّة يعني حفظاً جزئياً لا يطلبه أحد. ولذلك يُطفأ العَلَمان
     معاً عند النجاح. */
  /* نصّ الحقل أثناء الكتابة، بمفتاح «معرّف الشركة:الحقل». وبدونه تُبتلع
     النقطة العشرية: «23.» تُقرأ رقماً فتعود 23 ويُمحى ما كُتب قبل إكماله.
     فالمعروض هو ما كتبه المالك حتى يترك الحقل، والمحسوب هو تأويله رقماً. */
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [dirtyPlan, setDirtyPlan] = useState(false);
  const [dirtyOrders, setDirtyOrders] = useState(false);
  const dirty = dirtyPlan || dirtyOrders;

  /* الخادم مصدر الحقيقة عند القراءة، والتحرير محليّ. ولا نستبدل تحريراً غير
     محفوظ بردٍّ متأخّر من الخادم — فذلك يمحو عمل المالك أمام عينيه. */
  useEffect(() => {
    if (data?.items && !dirty) {
      setRows(data.items);
      // بلا قيمةٍ محفوظة تبدأ الدفعة بالسيولة كاملةً — وهو الافتراض الطبيعي:
      // ما لديك هو ما تخطّط لضخّه حتى تقرّر غيره.
      setTranche(String(data.tranche_value || data.available_cash || 0));
      setDraft({});
    }
  }, [data, dirty]);

  const trancheValue = Number(tranche) || 0;

  const save = useMutation({
    mutationFn: () => liquidityApi.save(
      rows.map(r => ({
        company_id: r.company_id,
        // النسبة التلقائية لا تُرسَل كرقم: إرسالها يجمّدها على وزن اليوم،
        // فتتوقّف عن متابعة المحفظة من غير أن يطلب المالك ذلك.
        ...(r.pct_is_auto ? { clear_share_pct: true } : { share_pct: r.share_pct }),
        tranches: r.tranches,
        exec_tranches: r.exec_tranches ?? 0,
        ...(r.price_is_override ? { price_override: r.price } : { clear_price_override: true }),
      })),
      trancheValue,
    ).then((r: any) => r.data),
    onSuccess: () => {
      setDirtyPlan(false);
      setDirtyOrders(false);
      setDraft({});
      qc.invalidateQueries({ queryKey: ["liquidity"] });
    },
  });

  const patch = (id: number, next: Partial<Row>, from: "plan" | "orders" = "plan") => {
    (from === "plan" ? setDirtyPlan : setDirtyOrders)(true);
    setRows(rs => rs.map(r => (r.company_id === id ? { ...r, ...next } : r)));
  };

  /* نفس معادلة الخادم حرفياً — تُعاد هنا للاستجابة الفورية وحدها، والقراءة
     التالية تأتي من الخادم فتكشف أي تباعُد لو وقع. */
  const calc = useMemo(() => {
    const items = rows.map(r => {
      const done = r.tranches.filter(Boolean).length;
      const pct = Number(r.share_pct) || 0;
      const reserved = trancheValue * pct / 100;
      const amount = reserved * done;
      // تداول لا يقبل جزء سهم: الكسر يُقرَّب للأسفل، فالمبلغ الإجمالي هو ما
      // يُخصم فعلاً لا ما رُصد — والفرق بينهما نقدٌ يبقى في الحساب.
      const price = Number(r.price) || 0;
      const shares = price > 0 ? Math.floor(amount / price) : 0;
      // أوامر الشراء بعدد دفعاتها هي — بطاقةٌ مستقلّة بقرارٍ مستقل.
      const execN = Number(r.exec_tranches) || 0;
      const execAmount = reserved * execN;
      const execShares = price > 0 ? Math.floor(execAmount / price) : 0;
      return { ...r, done, pct, reserved, amount, price, shares, total: shares * price,
               execN, execAmount, execShares, execTotal: execShares * price };
    });
    return {
      items,
      pctTotal: items.reduce((a, x) => a + x.pct, 0),
      amountTotal: items.reduce((a, x) => a + x.amount, 0),
      sharesTotal: items.reduce((a, x) => a + x.execShares, 0),
      grandTotal: items.reduce((a, x) => a + x.execTotal, 0),
    };
  }, [rows, trancheValue]);

  const pctOff = Math.abs(calc.pctTotal - 100) > 0.05;

  if (isLoading) return <div className="p-4 text-[var(--ink-muted)] text-sm">جارٍ التحميل…</div>;
  if (!rows.length) return <div className="p-4 text-[var(--ink-muted)] text-sm">لا مراكز لبناء خطّة عليها.</div>;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <Droplets size={15} className="text-[var(--brand-ink)]" />
          <h2 className="card-title">إدارة السيولة</h2>
          <div className="mr-auto flex items-center gap-2">
            {/* الدفعة مُدمَجة في شريط البطاقة: التسمية داخل الإطار لا فوقه،
                فيبقى ارتفاع الشريط واحداً ولا ينكسر السطر بجانب زر الحفظ. */}
            <div className="flex items-center gap-2 rounded-lg ps-2.5 pe-1 py-1"
              style={{ background: "transparent", border: "1px solid var(--hairline)" }}>
              <span className="text-[11px] text-[var(--brand)] whitespace-nowrap">الدفعة</span>
              <NumInput className="text-[14px] font-bold tabular-nums bg-transparent border-0 outline-none text-[var(--ink)] p-0"
                style={{ width: 84, textAlign: "start" }}
                value={tranche}
                onChange={(v: string) => { setDirtyPlan(true); setTranche(v); }} />
            </div>
            {dirtyPlan && <span className="unsaved-tag">غير محفوظ</span>}
            {/* زرّ الحفظ واحدٌ في التطبيق كلّه: أيقونة قرصٍ وحدها، واسمُه في
                `title`. كان هنا أيقونةً ونصّاً وفي «التوزيع النسبي» أيقونةً
                وحدها — زرّان لفعلٍ واحد بشكلين. */}
            <button className="btn-primary" onClick={() => save.mutate()}
              title={save.isPending ? "جارٍ الحفظ…" : "حفظ"} aria-label="حفظ"
              disabled={!dirtyPlan || save.isPending}>
              <Save size={15} />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto hidden md:block">
          <table className="w-full">
            <thead><tr className="border-b border-[var(--hairline)]">
              <th className="th text-start">الشركة</th>
              <th className="th text-start">النسبة المستهدفة %</th>
              {[1, 2, 3, 4, 5].map(i => <th key={i} className="th text-center">{i}</th>)}
              <th className="th text-start">المبلغ</th>
            </tr></thead>
            <tbody>
              {calc.items.map(r => (
                <tr key={r.company_id}>
                  <td className="td text-start">
                    <div className="flex items-center gap-2 min-w-0">
                      <CompanyLogo symbol={r.symbol} size={20} />
                      <span className="text-[12.5px] text-[var(--ink)] font-semibold truncate">{r.name}</span>
                    </div>
                  </td>
                  <td className="td text-start">
                    <div className="flex items-center gap-1">
                      <Field draft={draft} setDraft={setDraft} id={r.company_id} field="pct" value={r.share_pct} width={72} decimals={2}
                        onNum={n => patch(r.company_id, { share_pct: n, pct_is_auto: false })} />
                      {!r.pct_is_auto && (
                        /* العودة إلى الوزن المستهدف. */
                        <button className="btn-ghost" style={{ padding: "3px 5px" }} title="الوزن المستهدف"
                          onClick={() => {
                            setDraft(d => { const n = { ...d }; delete n[`${r.company_id}:pct`]; return n; });
                            patch(r.company_id, { pct_is_auto: true });
                          }}>
                          <RotateCcw size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                  {r.tranches.map((on, i) => (
                    <td key={i} className="td text-center">
                      <input type="checkbox" checked={on} className="w-4 h-4 cursor-pointer"
                        onChange={e => {
                          const next = [...r.tranches];
                          next[i] = e.target.checked;
                          patch(r.company_id, { tranches: next });
                        }} />
                    </td>
                  ))}
                  <td className="td text-start">
                    <span className="text-[13px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(r.amount)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ borderTop: "2px solid var(--hairline)" }}>
                <td className="td text-start text-[var(--ink-muted)] text-xs font-semibold">المجموع</td>
                <td className="td text-start">
                  <span className="text-[12px] font-bold tabular-nums" dir="ltr"
                    style={{ color: pctOff ? "var(--warn-ink)" : "var(--brand-ink)" }}>{fmt(calc.pctTotal, 2)}%</span>
                </td>
                <td className="td" colSpan={5} />
                <td className="td text-start">
                  <span className="text-[13px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(calc.amountTotal)}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* الجوّال: بطاقةٌ لكل شركة. الجدول أفقيّ بطبعه، وحشره في شاشةٍ ضيّقة
            يُنتج تمريراً جانبياً وحقولاً لا تُصاب بالإصبع. */}
        <div className="md:hidden space-y-2">
          {calc.items.map(r => (
            <div key={r.company_id} className="rounded-xl p-3 space-y-2.5"
              style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
              <div className="flex items-center gap-2 min-w-0">
                <CompanyLogo symbol={r.symbol} size={22} />
                <span className="text-[13px] text-[var(--ink)] font-semibold truncate">{r.name}</span>
                <span className="mr-auto text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(r.amount)}</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-[var(--ink-muted)] whitespace-nowrap">النسبة المستهدفة %</span>
                <Field draft={draft} setDraft={setDraft} id={r.company_id} field="pct" value={r.share_pct} width={80} decimals={2}
                  onNum={n => patch(r.company_id, { share_pct: n, pct_is_auto: false })} />
                {!r.pct_is_auto && (
                  <button className="btn-ghost" style={{ padding: "4px 6px" }} title="الوزن المستهدف"
                    onClick={() => {
                      setDraft(d => { const n = { ...d }; delete n[`${r.company_id}:pct`]; return n; });
                      patch(r.company_id, { pct_is_auto: true });
                    }}>
                    <RotateCcw size={13} />
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-[var(--ink-muted)] whitespace-nowrap">الدفعات</span>
                <div className="flex items-center gap-1.5">
                  {r.tranches.map((on, i) => (
                    /* مربّعات أكبر على الجوّال — هدف الإصبع لا يقلّ عن ٤٤ بكسل
                       في التوصيات، وسهم الفأرة وحده هو من يصيب ١٦ بكسل. */
                    <label key={i} className="flex items-center justify-center rounded-lg cursor-pointer"
                      style={{ width: 34, height: 34,
                        background: on ? "color-mix(in srgb, var(--pos-ink) 15%, transparent)" : "var(--bg)",
                        border: `1px solid ${on ? "color-mix(in srgb, var(--pos-ink) 45%, transparent)" : "var(--line)"}` }}>
                      <input type="checkbox" checked={on} className="w-4 h-4 cursor-pointer"
                        onChange={e => {
                          const next = [...r.tranches];
                          next[i] = e.target.checked;
                          patch(r.company_id, { tranches: next });
                        }} />
                    </label>
                  ))}
                </div>
              </div>
            </div>
          ))}

          <div className="flex items-center gap-2 pt-2" style={{ borderTop: "2px solid var(--hairline)" }}>
            <span className="text-xs font-semibold text-[var(--ink-muted)]">المجموع</span>
            <span className="text-[12px] font-bold tabular-nums" dir="ltr"
              style={{ color: pctOff ? "var(--warn-ink)" : "var(--brand-ink)" }}>{fmt(calc.pctTotal, 2)}%</span>
            <span className="mr-auto text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(calc.amountTotal)}</span>
          </div>
        </div>
      </div>

      {/* التنفيذ — ما يُشترى فعلاً. الأعلى قرار توزيع، وهذه ترجمته إلى أوامر:
          عدد أسهمٍ عند سعرٍ معلوم بمبلغٍ يُخصم من الحساب. */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <ClipboardList size={15} className="text-[var(--pos-ink)]" />
          <h2 className="card-title">أوامر الشراء</h2>
          <div className="mr-auto flex items-center gap-2">
            {dirtyOrders && <span className="unsaved-tag">غير محفوظ</span>}
            <button className="btn-primary" onClick={() => save.mutate()}
              title={save.isPending ? "جارٍ الحفظ…" : "حفظ"} aria-label="حفظ"
              disabled={!dirtyOrders || save.isPending}>
              <Save size={15} />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto hidden md:block">
          <table className="w-full">
            <thead><tr className="border-b border-[var(--hairline)]">
              <th className="th text-start">الشركة</th>
              <th className="th text-start">عدد الدفعات</th>
              <th className="th text-start">عدد الأسهم</th>
              <th className="th text-start">السعر</th>
              <th className="th text-start">المبلغ الإجمالي</th>
            </tr></thead>
            <tbody>
              {calc.items.map(r => (
                <tr key={r.company_id}>
                  <td className="td text-start">
                    <div className="flex items-center gap-2 min-w-0">
                      <CompanyLogo symbol={r.symbol} size={20} />
                      <span className="text-[12.5px] text-[var(--ink)] font-semibold truncate">{r.name}</span>
                    </div>
                  </td>
                  {/* عدد الدفعات رقمٌ هنا ومربّعاتٌ فوق، وهما شيءٌ واحد: كتابة
                      «٣» تؤشّر أوّل ثلاثة، فلا تتباعد البطاقتان أبداً. */}
                  <td className="td text-start">
                    <Field draft={draft} setDraft={setDraft} id={r.company_id} field="execN" value={r.execN} width={60} allowDecimal={false}
                      onNum={v => patch(r.company_id, { exec_tranches: Math.max(0, Math.min(5, Math.floor(v))) }, "orders")} />
                  </td>
                  <td className="td text-start">
                    <span className="text-[13px] font-bold tabular-nums" dir="ltr"
                      style={{ color: r.execShares > 0 ? "var(--pos-ink)" : "var(--ink-muted)" }}>{fmt(r.execShares)}</span>
                  </td>
                  <td className="td text-start">
                    <div className="flex items-center gap-1">
                      <Field draft={draft} setDraft={setDraft} id={r.company_id} field="price" value={r.price} width={78}
                        onNum={n => patch(r.company_id, { price: n, price_is_override: true }, "orders")} />
                      {r.price_is_override && (
                        /* السعر اليدوي يتقادم بصمت، ولا رجوع عنه بلا زرٍّ صريح. */
                        <button className="btn-ghost" style={{ padding: "3px 5px" }} title="سعر السوق"
                          onClick={() => {
                            setDraft(d => { const n = { ...d }; delete n[`${r.company_id}:price`]; return n; });
                            patch(r.company_id, { price: r.live_price, price_is_override: false }, "orders");
                          }}>
                          <RotateCcw size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="td text-start">
                    <span className="text-[13px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(r.execTotal)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ borderTop: "2px solid var(--hairline)" }}>
                <td className="td text-start text-[var(--ink-muted)] text-xs font-semibold">المجموع</td>
                <td className="td" />
                <td className="td text-start">
                  <span className="text-[13px] font-bold tabular-nums" dir="ltr" style={{ color: "var(--pos-ink)" }}>
                    {fmt(calc.sharesTotal)}
                  </span>
                </td>
                <td className="td" />
                <td className="td text-start">
                  <span className="text-[13px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(calc.grandTotal)}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="md:hidden space-y-2">
          {calc.items.map(r => (
            <div key={r.company_id} className="rounded-xl p-3 space-y-2.5"
              style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
              <div className="flex items-center gap-2 min-w-0">
                <CompanyLogo symbol={r.symbol} size={22} />
                <span className="text-[13px] text-[var(--ink)] font-semibold truncate">{r.name}</span>
                <span className="mr-auto text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(r.execTotal)}</span>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-[var(--ink-muted)]">الدفعات</span>
                <Field draft={draft} setDraft={setDraft} id={r.company_id} field="execN" value={r.execN} width={56} allowDecimal={false}
                  onNum={v => patch(r.company_id, { exec_tranches: Math.max(0, Math.min(5, Math.floor(v))) }, "orders")} />
                <span className="text-[11px] text-[var(--ink-muted)] ms-1">السعر</span>
                <Field draft={draft} setDraft={setDraft} id={r.company_id} field="price" value={r.price} width={78}
                  onNum={n => patch(r.company_id, { price: n, price_is_override: true }, "orders")} />
                {r.price_is_override && (
                  <button className="btn-ghost" style={{ padding: "4px 6px" }} title="سعر السوق"
                    onClick={() => {
                      setDraft(d => { const n = { ...d }; delete n[`${r.company_id}:price`]; return n; });
                      patch(r.company_id, { price: r.live_price, price_is_override: false }, "orders");
                    }}>
                    <RotateCcw size={13} />
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-[var(--ink-muted)]">عدد الأسهم</span>
                <span className="text-[14px] font-bold tabular-nums" dir="ltr"
                  style={{ color: r.execShares > 0 ? "var(--pos-ink)" : "var(--ink-muted)" }}>{fmt(r.execShares)}</span>
              </div>
            </div>
          ))}

          <div className="flex items-center gap-2 pt-2" style={{ borderTop: "2px solid var(--hairline)" }}>
            <span className="text-xs font-semibold text-[var(--ink-muted)]">المجموع</span>
            <span className="text-[13px] font-bold tabular-nums" dir="ltr" style={{ color: "var(--pos-ink)" }}>
              {fmt(calc.sharesTotal)}
            </span>
            <span className="mr-auto text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(calc.grandTotal)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
