import React, { useState } from "react";
import { invalidateWatchlist } from "../services/watchlistCache";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight, Plus, X, TrendingUp, TrendingDown, Coins, Activity, Layers, Pencil, Trash2, Check, Sparkles, Star
} from "lucide-react";
import {
  companiesApi, holdingsApi, dividendsApi, transactionsApi, marketApi, allocationApi, cashApi
} from "../services/api";
import { lookupCompany } from "../data/saudiCompanies";
import { useAuthStore } from "../store/authStore";
import CompanyLogo from "../components/common/CompanyLogo";
import { ShariaBadge, ShariaStatusIndicator, NumInput } from "../components/common/UI";
import AnalysisPanel from "../components/analysis/AnalysisPanel";
import FinancialsTable from "../components/analysis/FinancialsTable";
import OwnershipBar from "../components/analysis/OwnershipBar";
import PriceChart from "../components/analysis/PriceChart";
import DividendProfile from "../components/analysis/DividendProfile";
import StockCalendar from "../components/analysis/StockCalendar";
import CompanyProfileCards from "../components/analysis/CompanyProfileCards";
import StockOpinion from "../components/analysis/StockOpinion";
import clsx from "clsx";

const fmt  = (n: number, dec = 2) => (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const fmt0 = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });

/* ══ صفٌّ واحدٌ لا ينكسر ولا يُمرَّر ══
   كانت `flex-wrap` تكسر السبعةَ سطرين على الجوّال. والتمريرُ الأفقيّ
   عيبٌ تصميميّ بنصّ المالك، فلا يُستبدَل به. فالحلُّ اسمٌ قصيرٌ للشاشة
   الضيّقة واسمٌ كاملٌ لما اتّسع — والمعنى محفوظٌ في الحالين. */
const TABS = [
  { id: "overview",  label: "نظرة عامة",     short: "نظرة" },
  { id: "analysis",  label: "تقييم الأداء",  short: "الأداء" },
  { id: "financials", label: "القوائم المالية", short: "القوائم" },
  { id: "txs",       label: "سجل العمليات",  short: "العمليات" },
  { id: "divs",      label: "التوزيعات",     short: "التوزيعات" },
  { id: "calendar",  label: "المفكرة",       short: "المفكرة" },
  { id: "opinion",   label: "رأي الذكاء",    short: "الذكاء", color: "var(--chart-3)" },
] as const;

// 4 simple rules, no exceptions: توزيع نقدي وبيع يزيدان السيولة دائمًا، شراء
// ينقصها دائمًا (بوسم اختياري توزيع/تصفية للتقارير فقط)، ومنحة الأسهم تزيد
// الكمية فقط بدون أي أثر على السيولة أو التكلفة.
const TX_TYPES = [
  { id: "BUY",      label: "شراء",       color: "var(--pos-ink)" },
  { id: "SELL",     label: "بيع",        color: "var(--neg-ink)" },
  { id: "DIVIDEND", label: "توزيع نقدي", color: "var(--warn-ink)" },
  { id: "BONUS",    label: "منحة أسهم",  color: "var(--chart-3)" },
  { id: "SPLIT",    label: "تجزئة",      color: "var(--chart-7)" },
];
const FUNDING_SOURCES = [
  // خياران لا ثلاثة: مالٌ جديد من خارج المحفظة، أو مالٌ عاد منها (توزيعات أو
  // حصيلة تصفية معاً — النقد لا لون له فالتفريق بينهما تصنيفٌ لا واقعة).
  { id: "",         label: "ضخ",              color: "var(--ink-muted)" },
  { id: "REINVEST", label: "إعادة استثمار",   color: "var(--chart-6)" },
];
const TX_LABEL: Record<string, { label: string; color: string }> =
  Object.fromEntries(TX_TYPES.map(t => [t.id, t]));

function Empty({ label = "لا توجد بيانات حالياً" }: { label?: string }) {
  return <div className="py-10 text-center text-[var(--ink-muted)] text-sm">{label}</div>;
}

function Stat({ label, value, sub, icon: Icon, ic, color, cls = "" }: any) {
  return (
    <div className="mc">
      <div className={"mc-icon " + ic}><Icon size={14} style={{ color }} /></div>
      <div className="mc-lbl">{label}</div>
      <div className={"mc-val " + cls}>{value}</div>
      {sub && <div className="mc-sub">{sub}</div>}
    </div>
  );
}

/* ── نبذة نشاط الشركة والإدارة التنفيذية ─────────────────────────────────
   المصدر Yahoo وحده. وما لا يوفّره Yahoo لا يُستجدى من مصدرٍ آخر ولا يُختلق —
   تُخفى البطاقة كلها بدل أن يبقى عنوانٌ فوق فراغ.

   ومصدر النبذة معلَنٌ في الواجهة عن قصد: نصّ Yahoo إنجليزي، فترجمته آلية،
   ونصٌّ مترجَم آلياً لا يجوز أن يُقرأ كإفصاحٍ رسمي.

   والإدارة التنفيذية ليست مجلس الإدارة: companyOfficers هم الرئيس التنفيذي
   والمالي ونحوهم، وYahoo لا يُوفّر تشكيل المجالس إطلاقاً. فتُعرض باسمها
   الصحيح، ولا يوجد قسمٌ لمجلس الإدارة لأن مصدره غير متاح. */
/* وسم «مترجَمة آلياً» أُزيل بقرار المالك: النصّ وصفُ نشاطٍ لا إفصاحٌ مالي،
   والوسم التحذيري بجانبه كان يوحي بريبةٍ لا محلّ لها. ويبقى وسم «نصّك
   المحفوظ» وحده — فهو يميّز ما كتبه المالك عمّا جاء من المصدر. */


/* Quick transaction modal — same engine/payload contract as PortfolioPage */
function TxModal({ companyId, onClose }: { companyId: number; onClose: () => void }) {
  const qc = useQueryClient();
  const [type, setType] = useState("BUY");
  const [fundingSource, setFundingSource] = useState("");
  const [f, setF] = useState({ shares: "", price: "", amount: "", factor: "2", date: new Date().toISOString().slice(0, 10) });
  const [preSplitOk, setPreSplitOk] = useState(false);
  // سياق القرار: كم تملك · متوسط تكلفتك · نقدك المتاح. كانت البطاقة عمياء عنه
  // فتقرّر ثم تكتشف الخطأ بعد الإرسال.
  const { data: holding } = useQuery({
    queryKey: ["holding", companyId],
    queryFn: () => holdingsApi.get(companyId).then(r => r.data.data).catch(() => null),
  });
  // نصيب هذا السهم من إعادة التوازن — بصنفيه: سيولة وإعادة استثمار، بنسبة
  // وزنه المستهدف من كلّ مصدر (نفس حساب بطاقة «التوزيع النسبي»).
  const { data: allocCtx } = useQuery({
    queryKey: ["allocation"],
    queryFn: () => allocationApi.get().then(r => r.data.data).catch(() => null),
    enabled: type === "BUY" || type === "SELL",
  });
  const { data: cashCtx } = useQuery({
    queryKey: ["cash"], queryFn: () => cashApi.get().then(r => r.data?.data),
    enabled: type === "BUY",
  });
  const myAlloc = (allocCtx?.items ?? []).find((x: any) => x.company_id === companyId);
  const shares0 = Number(holding?.total_shares ?? 0);
  const invested0 = Number(holding?.invested_amount ?? 0);
  const addQty = Number(f.shares) || 0;
  const newAvgCost = (shares0 + addQty) > 0
    ? (invested0 + addQty * (Number(f.price) || 0)) / (shares0 + addQty) : 0;
  const set = (k: string) => (e: any) => setF(v => ({ ...v, [k]: e.target.value }));
  const setV = (k: string) => (v: string) => setF(o => ({ ...o, [k]: v }));
  /* تبديل النوع يُصفّر الحقول الرقمية — قيمةٌ محمولة من نوعٍ سابق تُسجَّل بلا
     انتباه وتعدّل حيازتك. */
  const changeType = (id: string) => {
    setType(id);
    setF(v => ({ ...v, shares: "", price: "", amount: "", factor: "2" }));
    if (id !== "BUY") setFundingSource("");
  };

  const mut = useMutation({
    mutationFn: () => {
      const payload: any = { company_id: companyId, transaction_type: type, transaction_date: f.date };
      if (type === "BUY" || type === "SELL") { payload.shares = Number(f.shares); payload.price_per_share = Number(f.price); }
      if (type === "BUY" && fundingSource) { payload.funding_source = fundingSource; }
      if (type === "DIVIDEND") { payload.amount = Number(f.amount); }
      if (type === "BONUS") {
        payload.shares = Number(f.shares);
        if (Number(f.price) > 0) payload.price_per_share = Number(f.price);
      }
      if (type === "SPLIT") { payload.factor = Number(f.factor); payload.confirm_prior_pre_split = preSplitOk; }
      return transactionsApi.add(payload).then(r => r.data);
    },
    onSuccess: () => { qc.invalidateQueries(); onClose(); },
  });

  const baseValid =
    (["BUY", "SELL"].includes(type) && Number(f.shares) > 0 && Number(f.price) > 0) ||
    (type === "DIVIDEND" && Number(f.amount) > 0) ||
    (type === "BONUS" && Number(f.shares) > 0) ||
    (type === "SPLIT" && Number(f.factor) > 0);

  /* نفس حراسات الخادم قبل الإرسال — منعٌ فوري بدل ضغطٍ وانتظارٍ ثم رفض. */
  const availCash = Number(cashCtx?.available_cash ?? 0);
  const blockReason: string | null =
    type === "SELL" && addQty > shares0 ? `لا تملك سوى ${fmt(shares0, 2)} سهم.`
    : type === "BUY" && cashCtx && addQty * (Number(f.price) || 0) > availCash
      ? `السيولة المتاحة ${fmt0(availCash)} لا تكفي.`
    : null;
  const valid = baseValid && !blockReason;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="modal-title">عملية جديدة</h3>
          <button className="text-[var(--ink-muted)] hover:text-[var(--ink)]" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-4">
          {TX_TYPES.map(t => (
            <button key={t.id} onClick={() => changeType(t.id)}
              className="py-2 rounded-xl text-xs font-bold transition-all border"
              style={type === t.id
                ? { background: `color-mix(in srgb, ${t.color} 14%, transparent)`, color: t.color,
                    borderColor: `color-mix(in srgb, ${t.color} 42%, transparent)` }
                : { borderColor: "var(--line)", color: "var(--ink-muted)" }}>
              {t.label}
            </button>
          ))}
        </div>
        {type === "BUY" && (
          <div className="grid grid-cols-2 gap-2 mb-4">
            {FUNDING_SOURCES.map(s => (
              <button key={s.id} onClick={() => setFundingSource(s.id)}
                className="py-1.5 rounded-lg text-[11px] font-bold transition-all border"
                style={fundingSource === s.id
                  ? { background: `color-mix(in srgb, ${s.color} 14%, transparent)`, color: s.color,
                      borderColor: `color-mix(in srgb, ${s.color} 42%, transparent)` }
                  : { borderColor: "var(--line)", color: "var(--ink-muted)" }}>
                {s.label}
              </button>
            ))}
          </div>
        )}
        <div className="tx-context grid grid-cols-3 gap-2 mb-3 text-center">
          <div><p className="text-[10px] text-[var(--ink-muted)]">أسهمك</p><p className="text-xs font-bold text-[var(--ink)] tabular-nums">{fmt(holding?.total_shares ?? 0, 2)}</p></div>
          <div><p className="text-[10px] text-[var(--ink-muted)]">متوسط التكلفة</p><p className="text-xs font-bold text-[var(--ink)] tabular-nums">{fmt(holding?.average_cost ?? 0)}</p></div>
          <div>
            <p className="text-[10px] text-[var(--ink-muted)]">نصيبه من التوازن</p>
            {/* بلا وزن مستهدف لا حصّة أصلاً — «لم يُحدَّد». مع وزنٍ، يُعرض
                بصنفيه: سيولة (أخضر) وإعادة استثمار (أزرق) — نفس نصيبه في
                بطاقة «التوزيع النسبي» تماماً. */}
            {!myAlloc || !Number(myAlloc.target_weight) ? (
              <p className="text-xs font-bold text-[var(--ink-muted)]">لم يُحدَّد</p>
            ) : (
              <div className="space-y-0.5">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[9.5px] text-[var(--ink-muted)]">سيولة</span>
                  <span className="text-[10px] font-bold tabular-nums text-[var(--pos-ink)]" dir="ltr">{fmt0(myAlloc.liquidity_share)}</span>
                </div>
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[9.5px] text-[var(--ink-muted)]">إعادة استثمار</span>
                  <span className="text-[10px] font-bold tabular-nums text-[var(--brand-ink)]" dir="ltr">{fmt0(myAlloc.reinvest_share)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="space-y-3">
          {["BUY", "SELL", "BONUS"].includes(type) && (
            <div><label className="label">عدد الأسهم</label><NumInput value={f.shares} onChange={setV("shares")} allowDecimal={false} /></div>
          )}
          {["BUY", "SELL"].includes(type) && (
            <div><label className="label">سعر السهم</label><NumInput value={f.price} onChange={setV("price")} /></div>
          )}
          {/* سعر يوم المنح — يُثبّت قيمة المنحة في «العائد المحقّق» فلا تتحرّك
              مع السوق كل يوم. اختياري: بدونه تُقدَّر بالسعر الأخير. */}
          {type === "BONUS" && (
            <div>
              <label className="label">سعر السهم يوم المنح</label>
              <NumInput placeholder="اختياري — يُثبّت قيمة المنحة في العائد المحقّق"
                value={f.price} onChange={setV("price")} />
            </div>
          )}
          {type === "DIVIDEND" && (
            <div><label className="label">مبلغ التوزيع</label><NumInput value={f.amount} onChange={setV("amount")} /></div>
          )}
          {type === "SPLIT" && (
            <>
              <div><label className="label">معامل التجزئة</label><NumInput value={f.factor} onChange={setV("factor")} /></div>
              {/* نفس حارس صفحة المحفظة: كميات الوسيط مُجزَّأة أصلاً، وتسجيل
                  التجزئة فوقها يضربها مرّتين ويفسد الحيازة صامتاً. */}
              <label className="flex items-start gap-2 text-[11px] leading-relaxed cursor-pointer rounded-xl p-3"
                style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
                <input type="checkbox" className="mt-0.5" checked={preSplitOk}
                  onChange={e => setPreSplitOk(e.target.checked)} />
                <span className="text-[var(--ink)]">
                  أُقرّ بأن كميات العمليات السابقة هي كميات <b>ما قبل التجزئة</b>.
                  <span className="block text-[var(--ink-muted)] mt-0.5">
                    إن كنت أدخلتها كما تظهر في تطبيق الوسيط اليوم فهي مُجزَّأة أصلاً.
                  </span>
                </span>
              </label>
            </>
          )}
          {type === "BUY" && addQty > 0 && Number(f.price) > 0 && (
            /* متوسط التكلفة بعد هذه الصفقة — قبل التنفيذ لا بعده. */
            <div className="tx-context flex items-center justify-between gap-3">
              <span className="text-xs text-[var(--ink-muted)]">متوسط التكلفة الجديد</span>
              <span className="text-xs text-[var(--brand-ink)] font-bold tabular-nums" dir="ltr">
                {fmt(newAvgCost)} <span className="text-[10px] text-[var(--ink-muted)]">(الآن {fmt(Number(holding?.average_cost ?? 0))})</span>
              </span>
            </div>
          )}
          <div><label className="label">التاريخ</label><input className="input" type="date" lang="en" max={new Date().toISOString().slice(0, 10)} value={f.date} onChange={set("date")} /></div>
        </div>
        {blockReason && baseValid && <p className="text-[var(--warn-ink)] text-xs mt-3">{blockReason}</p>}
        <button className="btn-primary w-full mt-4" disabled={!valid || mut.isPending} onClick={() => mut.mutate()}>
          {mut.isPending ? "جارٍ الحفظ…" : "تنفيذ العملية"}
        </button>
      </div>
    </div>
  );
}


/* Transaction row — deletable; reverses its cash/holding effect on the server */
/* حذف عملية — منطقٌ واحد يخدم صفّ الكمبيوتر وبطاقة الجوال، فلا تتباعد رسالة
   التأكيد ولا سلوك الحذف بين الشكلين. */
function useTxDelete(t: any) {
  const qc = useQueryClient();
  const mut = useMutation({
    mutationFn: () => transactionsApi.remove(t.id).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
  });
  const ask = () => {
    if (confirm("هل تريد حذف هذه العملية؟ سيتم عكس أثرها على الرصيد والمحفظة.")) mut.mutate();
  };
  return { mut, ask };
}

/* تحرير كامل لعمليةٍ مسجَّلة — الكمية · السعر · الرسوم · المبلغ · التاريخ ·
   الوسم. النوع وحده غير قابل للتغيير (تحويله يستوجب إعادة بناء علاقاتٍ أخرى،
   ومكانه حذف العملية وتسجيلها من جديد).

   السلامة على الخادم لا هنا: يعكس أثر النقد القديم بالضبط ثم يطبّق الجديد
   بنفس جدول الحذف، ويعيد بناء الحيازة من إعادة تشغيل السجل كاملاً — فتصحّ
   الكمية والتكلفة والأرباح المحقّقة مهما تغيّر الترتيب أو تخلّلته تجزئة. */
function useTxEdit(t: any) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const blank = () => ({
    quantity: String(t.quantity ?? ""),
    price: String(t.price ?? ""),
    amount: String(t.total ?? ""),
    date: t.date ? String(t.date).slice(0, 10) : "",
    funding_source: t.funding_source || "",
  });
  const [f, setF] = useState(blank);
  const set = (k: string) => (e: any) => setF(v => ({ ...v, [k]: e.target.value }));
  const setV = (k: string) => (v: string) => setF(o => ({ ...o, [k]: v }));

  const open = () => { setF(blank()); setErr(null); setEditing(true); };

  const mut = useMutation({
    mutationFn: (payload: any) => transactionsApi.patch(t.id, payload).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); setEditing(false); setErr(null); },
    onError: (e: any) => setErr(e?.response?.data?.detail || "تعذّر الحفظ."),
  });

  const save = () => {
    const p: any = {};
    if (["BUY", "SELL", "BONUS", "SPLIT"].includes(t.type)) p.quantity = Number(f.quantity) || 0;
    if (["BUY", "SELL", "BONUS"].includes(t.type)) p.price = Number(f.price) || 0;
    if (t.type === "DIVIDEND") p.amount = Number(f.amount) || 0;
    if (f.date) p.executed_at = f.date;
    if (t.type === "BUY") { p.set_funding_source = true; p.funding_source = f.funding_source; }
    mut.mutate(p);
  };

  return { editing, open, close: () => { setEditing(false); setErr(null); }, f, set, setF, mut, save, err };
}

/* نموذج التحرير — واحدٌ يخدم بطاقة الجوال وصفّ الكمبيوتر، فلا تتباعد الحقول
   ولا رسائل الخطأ بين الشكلين. الحقول المعروضة تتبع نوع العملية: لا معنى
   لسعرٍ في توزيعٍ نقدي ولا لمبلغٍ في تجزئة. */
function TxEditForm({ t, ed, all = [] }: { t: any; ed: any; all?: any[] }) {
  /* اقتراح سعر يوم المنح من سجلّك أنت — لا من مصدرٍ خارجي.
     المشكلة التي يحلّها: تحديد سعر يوم المنح يلتبس إن وقعت تجزئةٌ في الفترة
     نفسها، فلا يدري المالك أيّ سعرٍ يكتب: ما قبلها أم ما بعدها. والجواب في
     سجلّه: أقرب عمليةٍ له بسعرٍ حقيقي في نفس الشركة — فهي مسجَّلة بنفس أساس
     التجزئة الذي بُنيت عليه كمياته وتكلفته، فيستحيل أن تتناقض معها. */
  const suggestion = React.useMemo(() => {
    if (t.type !== "BONUS") return null;
    const target = t.date ? new Date(t.date).getTime() : Date.now();
    const cands = (all || [])
      .filter(x => x.id !== t.id && Number(x.price) > 0 && ["BUY", "SELL"].includes(x.type) && x.date)
      .map(x => ({ ...x, gap: Math.abs(new Date(x.date).getTime() - target) }))
      .sort((a, b) => a.gap - b.gap);
    if (!cands.length) return null;
    const c = cands[0];
    return {
      price: Number(c.price),
      days: Math.round(c.gap / 86400000),
      kind: c.type === "BUY" ? "شراء" : "بيع",
      date: new Date(c.date).toLocaleDateString("en-GB"),
    };
  }, [t, all]);

  /* الحقل مكوّنٌ في المستوى الأعلى (NumInput) لا دالةً معرّفة هنا: تعريفه داخل
     العرض كان يُنشئ نوعاً جديداً مع كل ضغطة مفتاح، فيُفكّك React الحقل ويُعيد
     بناءه ويضيع التركيز — وهو ما يُقرأ «توقّف التحرير فجأة». */
  const F = (label: string, k: string) => (
    <div key={k}>
      <label className="label">{label}</label>
      <NumInput value={(ed.f as any)[k]} onChange={(v: string) => ed.setF((o: any) => ({ ...o, [k]: v }))} />
    </div>
  );
  return (
    <div className="space-y-2.5 py-1">
      <div className="grid grid-cols-2 gap-2.5">
        {["BUY", "SELL", "BONUS"].includes(t.type) && F("عدد الأسهم", "quantity")}
        {t.type === "SPLIT" && F("معامل التجزئة", "quantity")}
        {["BUY", "SELL"].includes(t.type) && F("سعر السهم", "price")}
        {t.type === "BONUS" && F("سعر السهم يوم المنح", "price")}
        {t.type === "DIVIDEND" && F("مبلغ التوزيع", "amount")}
        <div>
          <label className="label">التاريخ</label>
          <input className="input" type="date" lang="en" max={new Date().toISOString().slice(0, 10)}
            value={ed.f.date} onChange={ed.set("date")} />
        </div>
      </div>

      {suggestion && (
        <div className="rounded-lg px-3 py-2" style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
          <p className="text-[10.5px] text-[var(--ink-muted)] leading-relaxed">
            أقرب سعر في سجلّك: <span className="text-[var(--ink)] font-bold tabular-nums" dir="ltr">{suggestion.price.toFixed(2)}</span>
            {" "}من عملية {suggestion.kind} بتاريخ <span dir="ltr">{suggestion.date}</span>
            {suggestion.days === 0 ? " — نفس اليوم" : ` — يبعد ${suggestion.days} يوماً`}.
            {" "}وهو مسجَّل بنفس أساس التجزئة الذي بُنيت عليه كمياتك، فلا يتناقض معها.
          </p>
          <button type="button" className="btn-ghost text-[11px] mt-1.5"
            onClick={() => ed.setF((v: any) => ({ ...v, price: String(suggestion.price) }))}>
            استخدم هذا السعر
          </button>
        </div>
      )}

      {t.type === "BUY" && (
        <div>
          <label className="label">مصدر التمويل</label>
          <div className="grid grid-cols-2 gap-2">
            {FUNDING_SOURCES.map(src => (
              <button key={src.id} type="button"
                onClick={() => ed.setF((v: any) => ({ ...v, funding_source: src.id }))}
                className="py-1.5 rounded-lg text-[11px] font-bold transition-all border"
                style={ed.f.funding_source === src.id
                  ? { background: `color-mix(in srgb, ${src.color} 14%, transparent)`, color: src.color,
                      borderColor: `color-mix(in srgb, ${src.color} 42%, transparent)` }
                  : { borderColor: "var(--line)", color: "var(--ink-muted)" }}>
                {src.label}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-[var(--ink-muted)] mt-1">
            «ضخ» = رأس مال جديد. «إعادة استثمار» = استُهلك من حوض العائد فيُنقصه.
          </p>
        </div>
      )}

      {ed.err && <p className="text-[var(--neg-ink)] text-[11px]">{ed.err}</p>}
      <div className="flex gap-2">
        <button className="btn-primary flex-1" disabled={ed.mut.isPending} onClick={ed.save}>
          {ed.mut.isPending ? "جارٍ الحفظ…" : "حفظ التعديل"}
        </button>
        <button className="btn-ghost" onClick={ed.close}>إلغاء</button>
      </div>
    </div>
  );
}

/* بطاقة عملية للجوال — بديل الصفّ الجدولي الذي كان بعرضٍ أدنى ٥٢٠px داخل
   تمرير أفقي، فيُقرأ بالسحب يميناً وشمالاً على الهاتف. رأسٌ (النوع + الوسم +
   التاريخ) ثم شبكة ثلاثية مصطفّة الأعمدة بين البطاقات فتُقارَن العمليات رأسياً. */
function TxCard({ t, all }: { t: any; all: any[] }) {
  const { isOwner } = useAuthStore();
  const m = TX_LABEL[t.type] || { label: t.type, color: "var(--ink-muted)" };
  const { mut, ask } = useTxDelete(t);
  const ed = useTxEdit(t);
  const isBonus = t.type === "BONUS";
  /* «الإجمالي» المخزَّن (total_amount) صفرٌ للمنحة دائماً — وهو صحيح ويجب أن
     يبقى: الحقل يمثّل النقد المتحرّك، والمنحة لا نقد فيها، وتغييره يُدخلها في
     حسابات السيولة. لكن عرض صفرٍ بعد إدخال سعر يوم المنح يبدو كأن التعديل لم
     يُحفظ. فتُحسب قيمة المنحة هنا لحظياً (الكمية × السعر) للعرض وحده. */
  const bonusValue = isBonus && Number(t.price) > 0
    ? Number(t.quantity || 0) * Number(t.price) : null;
  return (
    <div className="py-3 space-y-2.5">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="px-2 py-0.5 rounded-lg text-[11px] font-bold shrink-0"
          style={{ background: m.color + "22", color: m.color }}>{m.label}</span>
        {t.type === "BUY" && t.funding_source && (
          <button type="button" disabled={!isOwner} onClick={isOwner ? ed.open : undefined}
            title={isOwner ? "تعديل مصدر التمويل" : undefined}
            className="px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0"
            style={{ background: "color-mix(in srgb, var(--chart-4) 14%, transparent)", color: "var(--chart-6)" }}>إعادة استثمار</button>
        )}
        <span className="text-[11px] text-[var(--ink-muted)] tabular-nums ms-auto" dir="ltr">
          {t.date ? new Date(t.date).toLocaleDateString("en-GB") : "—"}
        </span>
        {isOwner && !ed.editing && (
          <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all shrink-0"
            title="تعديل العملية" onClick={ed.open}><Pencil size={13} /></button>
        )}
        {isOwner && (
          <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all shrink-0"
            title="حذف" disabled={mut.isPending} onClick={ask}><Trash2 size={13} /></button>
        )}
      </div>
      {ed.editing ? (
        <TxEditForm t={t} ed={ed} all={all} />
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {([["الكمية", fmt(t.quantity, 2)],
             [isBonus ? "سعر يوم المنح" : "السعر", isBonus && !(t.price > 0) ? "لم يُحدَّد" : fmt(t.price)],
             [isBonus ? "قيمة المنحة" : "الإجمالي", bonusValue != null ? fmt0(bonusValue) : (isBonus ? "—" : fmt0(t.total))]] as [string, string][]).map(([lbl, v]) => (
            <div key={lbl}>
              <p className="text-[10px] text-[var(--ink-muted)] whitespace-nowrap">{lbl}</p>
              <p className={"text-xs font-bold tabular-nums " + (v === "لم يُحدَّد" ? "text-[var(--warn-ink)]" : "text-[var(--ink)]")} dir="ltr">{v}</p>
            </div>
          ))}
          {/* الربح المحقّق للبيع: كان محسوباً ومخزَّناً ويغذّي الدخل والتقارير،
              ولا يُعرض في السجلّ. فيرى المالك «الإجمالي» (حصيلة البيع) ويقرؤه
              ربحاً — والفرق بينهما رأس ماله عائداً إليه. */}
          {t.type === "SELL" && t.realized_gain != null && (
            <div className="col-span-3 pt-1.5" style={{ borderTop: "1px solid var(--hairline)" }}>
              <p className="text-[10px] whitespace-nowrap" style={{ color: "var(--ink-muted)" }}>
                الربح المحقّق من هذا البيع
              </p>
              <p className="text-xs font-bold tabular-nums" dir="ltr"
                style={{ color: Number(t.realized_gain) >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                {Number(t.realized_gain) >= 0 ? "+" : ""}{fmt0(t.realized_gain)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TxRow({ t, all }: { t: any; all: any[] }) {
  const { isOwner } = useAuthStore();
  const m = TX_LABEL[t.type] || { label: t.type, color: "var(--ink-muted)" };
  const { mut: deleteMut, ask } = useTxDelete(t);
  const ed = useTxEdit(t);
  const isBonus = t.type === "BONUS";
  /* «الإجمالي» المخزَّن (total_amount) صفرٌ للمنحة دائماً — وهو صحيح ويجب أن
     يبقى: الحقل يمثّل النقد المتحرّك، والمنحة لا نقد فيها، وتغييره يُدخلها في
     حسابات السيولة. لكن عرض صفرٍ بعد إدخال سعر يوم المنح يبدو كأن التعديل لم
     يُحفظ. فتُحسب قيمة المنحة هنا لحظياً (الكمية × السعر) للعرض وحده. */
  const bonusValue = isBonus && Number(t.price) > 0
    ? Number(t.quantity || 0) * Number(t.price) : null;
  /* أثناء التحرير: صفٌّ واحد بعرض الجدول كاملاً يحمل النموذج نفسه المستعمل
     على الجوال — أوضح من حشر حقولٍ داخل خلايا ضيّقة، وأضمن لتطابق السلوك. */
  if (ed.editing) {
    return (
      <tr>
        <td className="td" colSpan={6}>
          <TxEditForm t={t} ed={ed} all={all} />
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td className="td">
        <span className="px-2 py-0.5 rounded-lg text-[11px] font-bold" style={{ background: m.color + "22", color: m.color }}>{m.label}</span>
        {t.type === "BUY" && t.funding_source && (
          <button type="button" disabled={!isOwner} onClick={isOwner ? ed.open : undefined}
            title={isOwner ? "تعديل مصدر التمويل" : undefined}
            className="ms-1 px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{
            background: "color-mix(in srgb, var(--chart-4) 14%, transparent)", color: "var(--chart-6)",
          }}>إعادة استثمار</button>
        )}
      </td>
      <td className="td tabular-nums">{fmt(t.quantity, 2)}</td>
      <td className="td tabular-nums">
        {isBonus && !(t.price > 0)
          ? <span className="text-[var(--warn-ink)] text-xs" title="بلا سعر يوم المنح تُقيَّم بسعر اليوم فتتحرّك مع السوق">لم يُحدَّد</span>
          : fmt(t.price)}
      </td>
      <td className="td tabular-nums">
        {bonusValue != null ? fmt0(bonusValue) : isBonus ? <span className="text-[var(--ink-muted)]">—</span> : fmt0(t.total)}
      </td>
      <td className="td text-[var(--ink-muted)]">{t.date ? new Date(t.date).toLocaleDateString("en-GB") : "—"}</td>
      <td className="td">
        <div className="flex items-center justify-end gap-1">
          {isOwner && (
            <>
              <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all"
                title="تعديل العملية" onClick={ed.open}><Pencil size={14} /></button>
              <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all" title="حذف"
                disabled={deleteMut.isPending} onClick={ask}>
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

/* تعديل/حذف توزيعة — منطقٌ واحد لصفّ الكمبيوتر وبطاقة الجوال معاً. */
function useDividendEdit(d: any) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(String(d.received ?? d.received_amount ?? 0));
  const invalidate = () => { qc.invalidateQueries(); };
  const updateMut = useMutation({
    mutationFn: () => {
      const shares = d.shares_at_time || 1;
      return dividendsApi.update(d.id, { dividend_per_share: Number(amount) / shares, shares_at_time: shares }).then(r => r.data);
    },
    onSuccess: () => { invalidate(); setEditing(false); },
  });
  const deleteMut = useMutation({
    mutationFn: () => dividendsApi.remove(d.id).then(r => r.data),
    onSuccess: invalidate,
  });
  const cancel = () => { setEditing(false); setAmount(String(d.received ?? 0)); };
  /* تأكيدٌ قبل الحذف — كان غائباً تماماً هنا بينما حذف العملية يسأله.
     وحذف التوزيعة ليس أقلّ خطراً: الخادم يعكس أثرها على السيولة وعلى إجمالي
     التوزيعات في الحيازة. فضغطةٌ واحدة على أيقونة ١٣px — يسهل خطؤها على
     الجوال — كانت تُغيّر أرقامك بلا رجعة ولا سؤال. */
  const askDelete = () => {
    if (deleteMut.isPending) return;
    const amt = Number(d.received ?? d.received_amount ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
    if (confirm(`حذف هذه التوزيعة (${amt} ﷼)؟ سيُعكس أثرها على السيولة وعلى إجمالي توزيعات هذه الشركة.`)) {
      deleteMut.mutate();
    }
  };
  return { editing, setEditing, amount, setAmount, updateMut, deleteMut, cancel, askDelete };
}

/* بطاقة توزيعة للجوال — بديل الصفّ الجدولي بعرضٍ أدنى ٤٨٠px داخل تمرير أفقي.
   يحتفظ بالتعديل الموضعي للمبلغ كما هو على الكمبيوتر تماماً. */
function DividendCard({ d }: { d: any }) {
  const { isOwner } = useAuthStore();
  const { editing, setEditing, amount, setAmount, updateMut, deleteMut, cancel, askDelete } = useDividendEdit(d);
  return (
    <div className="py-3 space-y-2.5">
      <div className="flex items-center gap-2 flex-wrap">
        {d.action === "REINVEST" ? <span className="tag-g shrink-0">إعادة استثمار</span> : <span className="tag-b shrink-0">نقدي</span>}
        <span className="text-[11px] text-[var(--ink-muted)] tabular-nums ms-auto" dir="ltr">
          {d.payment_date ? new Date(d.payment_date).toLocaleDateString("en-GB") : "—"}
        </span>
        {isOwner && (editing ? (
          <span className="flex items-center gap-1 shrink-0">
            <button className="p-1 rounded-lg text-[var(--pos-ink)]" title="حفظ"
              disabled={updateMut.isPending} onClick={() => updateMut.mutate()}><Check size={13} /></button>
            <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--ink)]" title="إلغاء" onClick={cancel}><X size={13} /></button>
          </span>
        ) : (
          <span className="flex items-center gap-1 shrink-0">
            <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all"
              title="تعديل المبلغ" onClick={() => setEditing(true)}><Pencil size={13} /></button>
            <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all"
              title="حذف" disabled={deleteMut.isPending} onClick={askDelete}><Trash2 size={13} /></button>
          </span>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] text-[var(--ink-muted)]">للسهم الواحد</p>
          <p className="text-xs font-bold text-[var(--ink)] tabular-nums" dir="ltr">{fmt(d.dividend_per_share)}</p>
        </div>
        <div>
          <p className="text-[10px] text-[var(--ink-muted)]">المستلم</p>
          {editing ? (
            <NumInput className="input" style={{ padding: "4px 8px" }} value={amount}
              onChange={setAmount} autoFocus />
          ) : (
            <p className="text-xs font-bold profit tabular-nums" dir="ltr">+{fmt0(d.received)}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* Dividend row — editable (amount) and deletable; both reverse/adjust cash + holding on the server */
function DividendRow({ d }: { d: any }) {
  const { isOwner } = useAuthStore();
  const { editing, setEditing, amount, setAmount, updateMut, deleteMut, cancel, askDelete } = useDividendEdit(d);

  return (
    <tr>
      <td className="td tabular-nums">{fmt(d.dividend_per_share)}</td>
      <td className="td tabular-nums profit">
        {editing ? (
          <NumInput className="input" style={{ width: 100, padding: "4px 8px" }} value={amount}
            onChange={setAmount} autoFocus />
        ) : (
          <>+{fmt0(d.received)}</>
        )}
      </td>
      <td className="td text-[var(--ink-muted)]">{d.payment_date ? new Date(d.payment_date).toLocaleDateString("en-GB") : "—"}</td>
      <td className="td">{d.action === "REINVEST" ? <span className="tag-g">إعادة استثمار</span> : <span className="tag-b">نقدي</span>}</td>
      <td className="td">
        <div className="flex items-center gap-1 justify-end">
          {!isOwner ? null : editing ? (
            <>
              <button className="p-1.5 rounded-lg text-[var(--pos-ink)]" title="حفظ"
                disabled={updateMut.isPending} onClick={() => updateMut.mutate()}><Check size={14} /></button>
              <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--ink)]" title="إلغاء"
                onClick={cancel}><X size={14} /></button>
            </>
          ) : (
            <>
              <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all" title="تعديل المبلغ"
                onClick={() => setEditing(true)}><Pencil size={14} /></button>
              <button className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all" title="حذف"
                disabled={deleteMut.isPending} onClick={askDelete}><Trash2 size={14} /></button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function CompanyPage() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");
  const [showTx, setShowTx] = useState(false);
  const { isOwner } = useAuthStore();

  const { data: company } = useQuery({ queryKey: ["company", id], queryFn: () => companiesApi.get(Number(id)).then(r => r.data.data) });

  /* المتابعة — نجمة تفتح قائمة مجموعات المراقبة.
     نجمةٌ واحدة لا تستطيع تمثيل عضويةٍ في عدّة قوائم ولا اختيار أيّها تُزيل
     منها، فجعلناها بوّابةً لا مفتاحاً: الضغط يفتح مجموعاتك مع علامة صحّ أمام
     ما هو عضوٌ فيه، وكل سطر يبدّل عضويته وحده. العضوية تُقرأ من الخادم بنداءٍ
     واحد (membership) لا باستعلام كل قائمة على حدة، فتبقى الواجهة مطابقةً
     لقاعدة البيانات لا لتخمينٍ محلّي. */
  const [watchOpen, setWatchOpen] = useState(false);
  const { data: groups = [] } = useQuery({
    queryKey: ["watchlist-groups"],
    queryFn: () => marketApi.watchGroups().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: watchOpen,
  });
  const { data: memberOf = [] } = useQuery({
    queryKey: ["watchlist-membership", company?.symbol],
    queryFn: () => marketApi.watchMembership(company!.symbol).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: !!company?.symbol,
  });
  const watched = memberOf.length > 0;
  const toggleWatch = useMutation({
    mutationFn: ({ gid, on }: { gid: number; on: boolean }) => (on
      ? marketApi.watchRemove(company!.symbol, gid)
      : marketApi.watchAdd(company!.symbol, company!.company_name, gid)),
    onSuccess: () => invalidateWatchlist(qc),
  });

  // Resolve Sharia status on demand the first time an unresolved stock is opened.
  const resolveSharia = useMutation({
    mutationFn: () => companiesApi.resolveSharia(Number(id)).then(r => r.data?.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["company", id] }),
  });
  React.useEffect(() => {
    if (company && (!company.sharia_status || company.sharia_status === "UNKNOWN") && !resolveSharia.isPending) {
      resolveSharia.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);
  const { data: holding } = useQuery({ queryKey: ["holding", id], queryFn: () => holdingsApi.get(Number(id)).then(r => r.data.data) });
  const { data: txs = [] } = useQuery({
    queryKey: ["transactions", id],
    queryFn: () => transactionsApi.list(Number(id)).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  const { data: divs = [] } = useQuery({
    queryKey: ["dividends", id],
    queryFn: () => dividendsApi.list().then(r => (Array.isArray(r.data.data) ? r.data.data : []).filter((d: any) => d.company_id === Number(id))),
  });
  const { data: analysis } = useQuery({
    queryKey: ["analysis", company?.symbol],
    queryFn: () => marketApi.company(company.symbol).then(r => r.data.data),
    enabled: !!company?.symbol,
    retry: 0,
  });
  /* الإنتاج ونقطة الصفر من الخادم — **نفس تعريف المحفظة حرفياً**.
     كان يُحسب في الواجهة: توزيعات + منحة×السعر + أسهم إعادة استثمار×السعر.
     وفيه خطآن: المنحة مزدوجة (قيمتها ضمن القيمة السوقية أصلاً)، وأسهم إعادة
     الاستثمار **مشتراةٌ بمالك** وثمنها في تكلفتك — فعدّ قيمتها إنتاجاً يحسب
     المال مرّتين. ولا تدخله حصيلة البيع وهي أكبر مكوّن في تعريف المحفظة.

     **وموضعه هنا مقصود**: كل نداءات useQuery يجب أن تسبق أي `return` مبكّر.
     كان أسفل حارس `if (!company)`، فيُنفَّذ في رندرٍ ولا يُنفَّذ في آخر —
     فيرمي React «Rendered more hooks than during the previous render» وتُطفأ
     الشاشة كاملةً (شاشة سوداء) لا صفحة الشركة وحدها. */
  const { data: prod } = useQuery({
    queryKey: ["holding-production", id],
    queryFn: () => holdingsApi.production(Number(id)).then(r => r.data.data),
    enabled: !!id,
    retry: 0,
  });
  if (!company) return <div className="flex items-center justify-center h-64 text-[var(--ink-muted)] text-sm">جارٍ تحميل بيانات الشركة...</div>;

  const ref = lookupCompany(company.symbol);
  const nameAr = company.name_ar || company.company_name_ar || ref?.name_ar || company.company_name;
  const nameEn = ref?.name_en || company.company_name;
  const profit = (holding?.market_value ?? 0) - (holding?.invested_amount ?? 0);
  const roi = holding?.invested_amount > 0 ? (profit / holding.invested_amount) * 100 : 0;
  const up = profit >= 0;
  const freeShares = (holding?.reinvestment_shares ?? 0) + (holding?.total_bonus_shares ?? 0);
  const bonusSharesValue = prod?.bonus_market_value ?? 0;
  const invested = prod?.invested ?? (holding?.invested_amount ?? 0);
  const stockProduction = prod?.total ?? 0;
  const capitalRecoveredPct = prod?.recovered_pct ?? 0;
  const remainingToRecover = prod?.remaining_to_recover ?? 0;
  const breakEvenReached = invested > 0 && stockProduction >= invested;

  return (
    <div className="space-y-5 fade-in">
      {/* Header — trilingual identity */}
      <div className="flex items-center gap-4 flex-wrap">
        <button className="btn-ghost text-sm flex items-center gap-1" onClick={() => nav("/portfolio")}>
          <ArrowRight size={15} /> المحفظة
        </button>
        <div className="flex items-center gap-3">
          <CompanyLogo symbol={company.symbol} color={company.color} size={44} logoUrl={company.logo_url} />
          <div>
            <div className="flex items-center gap-2">
              <ShariaBadge status={company.sharia_status} size={15} />
              {/* عنوان الصفحة لا نافذة — يبقى بمقاسه الأكبر المستقلّ. */}
              <h2 className="text-lg font-bold text-[var(--ink)]">{nameAr}</h2>
              <span className="tag-b">{company.symbol}</span>
              {isOwner && (
                <span className="relative shrink-0">
                  <button onClick={() => setWatchOpen(o => !o)} aria-expanded={watchOpen}
                    title={watched ? `متابَعة في ${memberOf.length} قائمة` : "إضافة إلى قائمة مراقبة"}
                    className={"watch-star p-1 rounded-lg transition-colors " + (watched ? "is-on" : "")}>
                    <Star size={17} fill={watched ? "currentColor" : "none"} />
                  </button>
                  {watchOpen && (
                    <>
                      {/* طبقة إغلاق شفافة: أي ضغطة خارج القائمة تُغلقها. */}
                      <span className="fixed inset-0 z-30" onClick={() => setWatchOpen(false)} />
                      <div className="watch-menu absolute z-40 top-full mt-1.5 end-0 w-56 rounded-xl shadow-xl overflow-hidden">
                        <p className="px-3 py-2 text-[11px] font-bold text-[var(--ink-muted)]">قوائم المراقبة</p>
                        {groups.length === 0 && (
                          <p className="px-3 pb-2.5 text-[11px] text-[var(--ink-muted)]">لا توجد قوائم بعد.</p>
                        )}
                        {groups.map((g: any) => {
                          const on = memberOf.includes(g.id);
                          return (
                            <button key={g.id} disabled={toggleWatch.isPending}
                              onClick={() => toggleWatch.mutate({ gid: g.id, on })}
                              className="watch-menu-row w-full flex items-center gap-2.5 px-3 py-2.5 text-start text-[13px]">
                              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: g.color }} />
                              <span className="flex-1 truncate">{g.name}</span>
                              {on && <Check size={14} className="text-[var(--pos-ink)] shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    </>
                  )}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-[var(--ink-muted)]">
              <span dir="ltr">{nameEn}</span>
              {company.sector && <span className="tag-n">{company.sector}</span>}
            </div>
          </div>
        </div>
        {isOwner && (
          <button className="btn-primary mr-auto flex items-center gap-1.5 text-sm" onClick={() => setShowTx(true)}>
            <Plus size={15} /> عملية جديدة
          </button>
        )}
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="القيمة السوقية" value={fmt0(holding?.market_value)} sub={`المدفوع: ${fmt0(holding?.invested_amount)}`} icon={Activity} ic="ic-b" color="var(--chart-2)" cls="b" />
        <Stat label="أرباح غير محققة" value={(up ? "+" : "") + fmt0(profit)} sub={(roi >= 0 ? "+" : "") + roi.toFixed(2) + "%"} icon={up ? TrendingUp : TrendingDown} ic={up ? "ic-g" : "ic-r"} color={up ? "var(--pos-ink)" : "var(--neg-ink)"} cls={up ? "g" : "r"} />
        <Stat label="متوسط التكلفة" value={fmt(holding?.average_cost)} sub={`آخر سعر: ${fmt(holding?.last_price)}`} icon={Coins} ic="ic-v" color="var(--chart-4)" />
        <Stat label="عدد الأسهم" value={fmt0(holding?.quantity)} sub={`أسهم مجانية: ${fmt(freeShares, 2)}`} icon={Layers} ic="ic-a" color="var(--warn-ink)" />
      </div>

      {/* ══ التبويبات: صفٌّ واحدٌ بلا إطار ══
          الحدُّ حول كلّ زرٍّ كان يصنع سبعةَ صناديقَ متجاورة فتبدو الشاشةُ
          مزدحمة. فالفاصلُ خطٌّ واحدٌ تحت الصفّ، والنشِطُ يُعلَّم بخطٍّ
          تحته ولونٍ — وهو العرفُ المهنيّ في التبويبات، وأخفُّ بصرياً. */}
      <div className="flex items-stretch gap-0.5 sm:gap-1 border-b border-[var(--hairline)]"
           role="tablist" aria-label="أقسام الشركة">
        {TABS.map(t => {
          const on = tab === t.id;
          const isAi = Boolean((t as any).color);
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              role="tab" aria-selected={on}
              /* min-w-0 يسمح للنصّ بالانكماش داخل flex بدل أن يدفع الصفَّ
                 إلى التمرير — بدونه يتجاوز العنصرُ عرضَ أبيه. */
              className={clsx(
                "flex-1 min-w-0 flex items-center justify-center gap-1",
                "px-0.5 sm:px-2 py-2 text-[10.5px] sm:text-xs font-bold",
                "border-b-2 -mb-px transition-colors whitespace-nowrap",
                on ? "border-[var(--brand)]" : "border-transparent",
                on ? (isAi ? "" : "text-[var(--brand-ink)]")
                   : "text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              {isAi && <Sparkles size={11} className={on ? "ai-star" : ""} />}
              <span className={clsx("truncate", isAi && on && "ai-opinion-text")}>
                <span className="sm:hidden">{t.short}</span>
                <span className="hidden sm:inline">{t.label}</span>
              </span>
            </button>
          );
        })}
      </div>

      {tab === "overview" && (
        <>
        <div className="card">
          <p className="card-title mb-3">التوافق الشرعي</p>
          <ShariaStatusIndicator status={company.sharia_status} loading={resolveSharia.isPending}
            purification={company.purification} source={company.sharia_source} />
        </div>
        {/* ══ حُذفت بطاقةُ «هدف المحللين» من النظرة العامّة ══
            (بأمر المالك · D208)
            كانت تحمل سعرَ الدخول وقد أُمر بحذفه، ورقمُها معروضٌ في تبويب
            «تقييم الأداء» — وهو تبويبٌ مشتركٌ بين الشاشتين. */}
        <PriceChart symbol={company.symbol} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card">
            <p className="card-title mb-3">إنتاج السهم</p>
            <div className="space-y-2 text-sm">
              <div className="stat-row"><span className="stat-lbl">توزيعات</span><span className="stat-val profit">+{fmt0(prod?.dividends ?? 0)}</span></div>
              <div className="stat-row"><span className="stat-lbl">حصيلة تصفية</span><span className="stat-val profit">+{fmt0(prod?.sale_proceeds ?? 0)}</span></div>
              <div className="stat-row"><span className="stat-lbl">ربح التصفية</span><span className="stat-val">{fmt0(prod?.sale_gains ?? 0)}</span></div>
              <div className="stat-row"><span className="stat-lbl">أسهم منحة</span><span className="stat-val">{fmt(prod?.bonus_shares ?? 0, 0)}</span></div>
              <div className="stat-row"><span className="stat-lbl">قيمة أسهم المنحة · ضمن القيمة السوقية</span><span className="stat-val">{fmt0(bonusSharesValue)}</span></div>
                            <div className="border-t border-[var(--hairline)] pt-2.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="stat-lbl font-bold">استرداد رأس المال</span>
                  <span className="stat-val" style={{ color: breakEvenReached ? "var(--pos-ink)" : "var(--chart-2)" }}>
                    {fmt(capitalRecoveredPct, 0)}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--surface)] overflow-hidden">
                  <div className="h-1.5 rounded-full transition-all" style={{ width: `${capitalRecoveredPct}%`, background: breakEvenReached ? "var(--pos-ink)" : "var(--chart-1)" }} />
                </div>
                <p className="text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">
                  {fmt0(stockProduction)} / {fmt0(invested)}
                  {!breakEvenReached && <> · {fmt0(remainingToRecover)}</>}
                </p>
              </div>
            </div>
          </div>
          <OwnershipBar symbol={company.symbol} />
        </div>
        {/* النبذة والإدارة في آخر الصفحة: مرجعٌ يُقرأ مرّةً لا رقمٌ يُتابَع
            يومياً، فمكانه بعد الأرقام التي تُفتح الصفحة لأجلها. */}
        <CompanyProfileCards companyId={Number(id)} />
        </>
      )}

      {tab === "analysis" && <AnalysisPanel symbol={company.symbol} name={nameAr} />}

      {tab === "financials" && <FinancialsTable symbol={company.symbol} />}

      {tab === "txs" && (
        <div className="card">
          <p className="card-title mb-3">سجل العمليات</p>
          {txs.length === 0 ? <Empty label="لا توجد عمليات مسجلة لهذه الشركة" /> : (
            <>
              {/* الجدول للكمبيوتر، والبطاقات للجوال — كصفحة الحيازات تماماً.
                  كان جدولاً واحداً بعرضٍ أدنى ٥٢٠px يُقرأ على الهاتف بالسحب
                  الأفقي، وهو سلوكٌ يخالف بقيّة التطبيق. */}
              <table className="w-full text-sm hidden md:table">
                <thead><tr>{["النوع", "الكمية", "السعر", "الإجمالي", "التاريخ", ""].map(h => <th key={h} className="th text-right">{h}</th>)}</tr></thead>
                <tbody>
                  {txs.map((t: any) => <TxRow key={t.id} t={t} all={txs} />)}
                </tbody>
              </table>
              <div className="md:hidden divide-y divide-[var(--hairline)]">
                {txs.map((t: any) => <TxCard key={t.id} t={t} all={txs} />)}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "divs" && (
        <div className="space-y-4">
          <DividendProfile symbol={company.symbol} />
          <div className="card">
            <p className="card-title mb-3">توزيعاتي المستلمة من هذه الشركة</p>
            {divs.length === 0 ? <Empty label="لم تُسجّل بعد أي توزيع مستلم لهذه الشركة في محفظتك" /> : (
              <>
                <table className="w-full text-sm hidden md:table">
                  <thead><tr>{["للسهم الواحد", "المستلم", "التاريخ", "الإجراء", ""].map(h => <th key={h} className="th text-right">{h}</th>)}</tr></thead>
                  <tbody>
                    {divs.map((d: any) => <DividendRow key={d.id} d={d} />)}
                  </tbody>
                </table>
                <div className="md:hidden divide-y divide-[var(--hairline)]">
                  {divs.map((d: any) => <DividendCard key={d.id} d={d} />)}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {tab === "calendar" && <StockCalendar symbol={company.symbol} name={nameAr} />}

      {tab === "opinion" && (
        <div className="card">
          <StockOpinion symbol={company.symbol} name={nameAr} />
        </div>
      )}

      {showTx && <TxModal companyId={Number(id)} onClose={() => setShowTx(false)} />}
    </div>
  );
}
