import React from "react";
import { Search, X } from "lucide-react";
import { searchCompanies, SaudiCompany } from "../../data/saudiCompanies";
import CompanyLogo from "../common/CompanyLogo";
import { marketApi } from "../../services/api";
import { isOption, optionTitle, parseOption } from "../../lib/options";

type Remote = { symbol: string; name: string; type: string; exchange: string; us: boolean };
const LATIN = /^[\^A-Za-z][A-Za-z0-9.=^ -]{0,24}$/;

/* ══ بحثٌ يتمدّد في محلّه ══ (بأمر المالك · D210)

   كان زرُّ البحث في ترويسة «نبض السوق» يفتح **بطاقةً كاملة** فوقها فيها
   مربّعٌ بتصميمٍ سابق — فيقفز التخطيطُ وتظهر شاشةٌ ثانيةٌ لفعلٍ صغير.
   الآن الزرُّ نفسُه يستطيل حقلاً في موضعه ويعود، بلا بطاقةٍ ولا قفزة.

   والتلاشي بالعرض والشفافية معاً، ويُحترَم `prefers-reduced-motion`
   فمن أوقف الحركةَ في نظامه لا تُفرَض عليه. */

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
    if (!global || !open || !LATIN.test(t) || isOption(t)) { setRemote([]); setBusy(false); return; }
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

  const close = () => { setOpen(false); setQ(""); setHits([]); setRemote([]); };

  React.useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  /* ضغطةٌ خارج الحقل تُغلقه — كالقوائم المنسدلة في التطبيق. */
  React.useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) close();
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
              const t = q.trim();
              pick(isOption(t) ? t : (global && LATIN.test(t) ? remote[0]?.symbol || hits[0]?.symbol : hits[0]?.symbol || remote[0]?.symbol) || t);
            }
            if (e.key === "Escape") close();
          }} />
      </div>

      {/* ══ السوقان في قائمةٍ واحدة ══ (بأمر المالك · D521 · ‏D761)
         كانت نتائجُ السوق الأمريكيّ لا تظهر إن وافق الحرفُ اسماً سعودياً («NIO» في «Union»…) — قائمتان في موضعٍ واحدٍ تُخفي إحداهما
         الأخرى. والآن قائمةٌ واحدة: عقدُ الخيار المنسوخ أوّلاً، ثمّ الأمريكيُّ (والحرفُ لاتينيّ)، ثمّ السعوديّ. */}
      {open && (hits.length > 0 || (global && (remote.length > 0 || isOption(q.trim()) || (!busy && /^[\^A-Za-z][A-Za-z0-9.=^-]{0,14}$/.test(q.trim()))))) && (
        <div className="sp-menu absolute z-30 top-full mt-1.5 end-0 rounded-xl overflow-hidden shadow-2xl" style={{ width: 300, maxHeight: 360, overflowY: "auto" }}
          data-role="search-remote">
          {global && isOption(q.trim()) && (
            <button type="button" onClick={() => pick(q.trim())} data-role="search-option"
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[36px] text-start hover:panel transition-colors">
              <CompanyLogo symbol={q.trim()} size={22} />
              <span className="text-[12.5px] font-bold text-[var(--ink)]">{optionTitle(parseOption(q.trim())!)}</span>
              <span className="text-[var(--ink-muted)] text-[11px] ms-auto">عقد خيار</span>
            </button>
          )}
          {global && !isOption(q.trim()) && remote.map(r => (
            <button key={r.symbol} type="button" onClick={() => pick(r.symbol)} data-role="search-hit"
              className="w-full flex items-center gap-2.5 px-2.5 py-2 min-h-[36px] text-start hover:panel transition-colors">
              <CompanyLogo symbol={r.symbol} size={22} />
              <span className="tabular-nums text-[12px] font-bold text-[var(--ink)] shrink-0" dir="ltr">{r.symbol}</span>
              <span className="text-[var(--ink)] text-[12px] truncate min-w-0" dir="ltr" style={{ textAlign: "right" }}>{r.name}</span>
              <span className="text-[var(--ink-muted)] text-[10.5px] ms-auto shrink-0">{r.type}{r.exchange ? ` · ${r.exchange}` : ""}</span>
            </button>
          ))}
          {global && !isOption(q.trim()) && !remote.length && !hits.length && !busy && (
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
        </div>
      )}
    </div>
  );
}
