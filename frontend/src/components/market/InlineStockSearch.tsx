import React from "react";
import { createPortal } from "react-dom";
import { Search, X } from "lucide-react";
import { mergeDirectory, searchCompanies, SaudiCompany } from "../../data/saudiCompanies";
import CompanyLogo from "../common/CompanyLogo";
import { marketApi } from "../../services/api";
import { optionTitle, parseOption, toOcc } from "../../lib/options";
import { normalizeSymbol } from "../../lib/symbols";

type Remote = { symbol: string; name: string; type: string; exchange: string; us: boolean };
const LATIN = /^[\^A-Za-z][A-Za-z0-9.=^ -]{0,24}$/;

/* ══ بحثٌ يتمدّد في محلّه ══ (بأمر المالك · D210)

   كان زرُّ البحث في ترويسة «نبض السوق» يفتح **بطاقةً كاملة** فوقها فيها
   مربّعٌ بتصميمٍ سابق — فيقفز التخطيطُ وتظهر شاشةٌ ثانيةٌ لفعلٍ صغير.
   الآن الزرُّ نفسُه يستطيل حقلاً في موضعه ويعود، بلا بطاقةٍ ولا قفزة.

   والتلاشي بالعرض والشفافية معاً، ويُحترَم `prefers-reduced-motion`
   فمن أوقف الحركةَ في نظامه لا تُفرَض عليه. */

/* ‏D787: دليلُ «تداول» الحيّ يُجلب مرّةً في الجلسة عند أوّل بحث، ويُضاف إلى القائمة الثابتة */
let dirOnce: Promise<void> | null = null;
const loadDirectory = () => (dirOnce ||= marketApi.saudiDirectory()
  .then(r => { const d = r.data?.data; if (d && Array.isArray(d.rows)) mergeDirectory(d.rows, !!d.complete); })
  .catch(() => { dirOnce = null; }));

export default function InlineStockSearch(
  { onPick, global = false }: { onPick: (symbol: string) => void; global?: boolean },
) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<SaudiCompany[]>([]);
  /* ‏D747: «قائمةُ البحث تشمل جميعَ أسهم السوق الأمريكي» — الحرفُ اللاتينيُّ يسأل خادمَنا عن السوق كلِّه (بعد توقّفٍ قصيرٍ في الكتابة) */
  const [remote, setRemote] = React.useState<Remote[]>([]);
  const [busy, setBusy] = React.useState(false);
  React.useEffect(() => {
    const t = q.trim();
    if (!global || !open || !LATIN.test(t) || toOcc(t)) { setRemote([]); setBusy(false); return; }
    let live = true;
    setBusy(true);
    const id = window.setTimeout(() => {
      marketApi.symbolSearch(t).then(r => { if (live) setRemote(Array.isArray(r.data?.data) ? r.data.data : []); })
        .catch(() => { if (live) setRemote([]); }).finally(() => { if (live) setBusy(false); });
    }, 260);
    return () => { live = false; window.clearTimeout(id); };
  }, [q, open, global]);
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const wrapRef = React.useRef<HTMLDivElement | null>(null);
  const menuRef = React.useRef<HTMLDivElement | null>(null);
  /* ══ القائمةُ فوق الصفحة لا داخلها ══ (‏D765 — المالك 2026-11-18: «نافذةُ نتائج البحث تظهر تحت القائمة الجانبية»)
     كانت مطلقةً داخل منطقة المحتوى وتمتدّ 300px نحو طرف الحقل البعيد — وفي غرفة التداول الحقلُ ملاصقٌ للقائمة الجانبية، ومنطقةُ المحتوى
     صندوقُ تمريرٍ يقصّ ما يخرج منه، فانقطعت النتائجُ تحت القائمة. فتُرسم الآن في جذر الصفحة ثابتةً تحت الحقل، تبدأ من طرفه القريب
     (يمينه في العربية) وتمتدّ نحو المحتوى، ومحصورةً داخل الشاشة، وتتبع الحقلَ عند التمرير وتغيّر الحجم. */
  const [pos, setPos] = React.useState<{ top: number; left: number; width: number; maxH: number; rtl: boolean } | null>(null);

  const close = () => { setOpen(false); setQ(""); setHits([]); setRemote([]); };

  React.useEffect(() => {
    if (open) { inputRef.current?.focus(); loadDirectory()?.then(() => { const t = inputRef.current?.value || ""; if (t) setHits(searchCompanies(t, 400)); }); }
  }, [open]);

  React.useLayoutEffect(() => {
    if (!open) { setPos(null); return; }
    const place = () => {
      const r = wrapRef.current?.getBoundingClientRect();
      if (!r) return;
      const vw = document.documentElement.clientWidth, vh = window.innerHeight;
      const width = Math.min(300, vw - 16);
      const rtl = getComputedStyle(wrapRef.current!).direction === "rtl";
      const left = Math.max(8, Math.min(rtl ? r.right - width : r.left, vw - width - 8));
      const top = r.bottom + 6;
      setPos({ top, left, width, maxH: Math.max(160, Math.min(360, vh - top - 8)), rtl });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => { window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [open, q]);

  /* ضغطةٌ خارج الحقل وقائمتِه تُغلقه — كالقوائم المنسدلة في التطبيق. */
  React.useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => {
      const t = e.target as Node;
      if (wrapRef.current && !wrapRef.current.contains(t) && !menuRef.current?.contains(t)) close();
    };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  const pick = (sym: string) => { close(); onPick(sym.toUpperCase()); };

  return (
    /* ══ لا `line-height: 0` على الحاوية ══
       وُضعت لإلغاء فراغ السطر حول الزرّ، فورثتها القائمةُ المنسدلة داخلها
       فانهار ارتفاعُ أسطرها إلى صفر: النصُّ موجودٌ في الشجرة ولا يُرى.
       قِيس: ارتفاعُ سطر الاسم 0px. والحاويةُ `inline-flex` تُغني عنها. */
    <div ref={wrapRef} className="relative ms-1 inline-flex items-center">
      <div className="inline-search" data-open={open ? "1" : "0"}>
        <button type="button" aria-label={open ? "إغلاق البحث" : "ابحث عن سهم"}
          title={open ? "إغلاق البحث" : "ابحث عن سهم"}
          onClick={() => (open ? close() : setOpen(true))}
          className="inline-search-btn">
          {open ? <X size={14} /> : <Search size={14} />}
        </button>
        <input ref={inputRef} className="inline-search-input" value={q}
          placeholder="بالرمز أو الاسم…"
          tabIndex={open ? 0 : -1}
          onChange={e => { setQ(e.target.value); setHits(searchCompanies(e.target.value, 400)); }}
          onKeyDown={e => {
            if (e.key === "Enter" && (hits[0] || remote[0] || q)) {
              /* ‏D787: رمزٌ ملصوقٌ يُفتح كما هو — عقدٌ بصيغتيه (‏OCC · تريدنق فيو)، أو ببادئة سوقه (‏TADAWUL:1120 · NASDAQ:NVDA)، أو «تاسي» */
              const t = q.trim(), occ = toOcc(t), code = /:/.test(t) || /^(تاسي|TASI)$/i.test(t) ? normalizeSymbol(t) : null;
              pick(occ || code || (global && LATIN.test(t) ? remote[0]?.symbol || hits[0]?.symbol : hits[0]?.symbol || remote[0]?.symbol) || t);
            }
            if (e.key === "Escape") close();
          }} />
      </div>

      {/* ══ السوقان في قائمةٍ واحدة ══ (بأمر المالك · D521 · ‏D761)
         كانت نتائجُ السوق الأمريكيّ لا تظهر إن وافق الحرفُ اسماً سعودياً («NIO» في «Union»…) — قائمتان في موضعٍ واحدٍ تُخفي إحداهما
         الأخرى. والآن قائمةٌ واحدة: عقدُ الخيار المنسوخ أوّلاً، ثمّ الأمريكيُّ (والحرفُ لاتينيّ)، ثمّ السعوديّ. */}
      {open && pos && (hits.length > 0 || (global && (remote.length > 0 || !!toOcc(q.trim()) || (!busy && /^[\^A-Za-z][A-Za-z0-9.=^-]{0,14}$/.test(q.trim()))))) && createPortal(
        <div ref={menuRef} dir={pos.rtl ? "rtl" : "ltr"} className="sp-menu search-pop rounded-xl overflow-hidden shadow-2xl"
          style={{ position: "fixed", top: pos.top, left: pos.left, width: pos.width, maxHeight: pos.maxH, overflowY: "auto" }}
          data-role="search-remote">
          {global && !!toOcc(q.trim()) && (
            <button type="button" onClick={() => pick(toOcc(q.trim())!)} data-role="search-option"
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[36px] text-start hover:panel transition-colors">
              <CompanyLogo symbol={toOcc(q.trim())!} size={22} />
              <span className="text-[12.5px] font-bold text-[var(--ink)]">{optionTitle(parseOption(toOcc(q.trim())!)!)}</span>
              <span className="text-[var(--ink-muted)] text-[11px] ms-auto">عقد خيار</span>
            </button>
          )}
          {global && !toOcc(q.trim()) && remote.map(r => (
            <button key={r.symbol} type="button" onClick={() => pick(r.symbol)} data-role="search-hit"
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[36px] text-start hover:panel transition-colors">
              <CompanyLogo symbol={r.symbol} size={22} />
              <span className="tabular-nums text-[12px] font-bold text-[var(--ink)] shrink-0" dir="ltr">{r.symbol}</span>
              <span className="text-[var(--ink)] text-[12px] truncate min-w-0" dir="ltr" style={{ textAlign: "right" }}>{r.name}</span>
              <span className="text-[var(--ink-muted)] text-[10.5px] ms-auto shrink-0">{r.type}{r.exchange ? ` · ${r.exchange}` : ""}</span>
            </button>
          ))}
          {global && !toOcc(q.trim()) && !remote.length && !hits.length && !busy && (
            <button type="button" onClick={() => pick(q.trim())}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[32px] text-start hover:panel transition-colors">
              <span className="tabular-nums text-[12px] font-semibold text-[var(--ink)]" dir="ltr">{q.trim().toUpperCase()}</span>
              <span className="text-[var(--ink-muted)] text-[12px]">سوقٌ عالميّ</span>
            </button>
          )}
          {hits.slice(0, 40).map(c => (
            <button key={c.symbol} type="button" onClick={() => pick(c.symbol)} data-role="search-sa"
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[32px] text-start hover:panel transition-colors">
              <CompanyLogo symbol={c.symbol} size={22} />
              <span className="tabular-nums text-[11px] font-semibold text-[var(--ink-muted)] shrink-0" dir="ltr">
                {c.symbol}
              </span>
              <span className="text-[var(--ink)] text-[13px] truncate">{c.name_ar}</span>
            </button>
          ))}
        </div>, document.body)}
    </div>
  );
}
