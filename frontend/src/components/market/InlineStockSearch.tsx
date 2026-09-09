import React from "react";
import { Search, X } from "lucide-react";
import { searchCompanies, SaudiCompany } from "../../data/saudiCompanies";
import CompanyLogo from "../common/CompanyLogo";

/* ══ بحثٌ يتمدّد في محلّه ══ (بأمر المالك · D210)

   كان زرُّ البحث في ترويسة «نبض السوق» يفتح **بطاقةً كاملة** فوقها فيها
   مربّعٌ بتصميمٍ سابق — فيقفز التخطيطُ وتظهر شاشةٌ ثانيةٌ لفعلٍ صغير.
   الآن الزرُّ نفسُه يستطيل حقلاً في موضعه ويعود، بلا بطاقةٍ ولا قفزة.

   والتلاشي بالعرض والشفافية معاً، ويُحترَم `prefers-reduced-motion`
   فمن أوقف الحركةَ في نظامه لا تُفرَض عليه. */

export default function InlineStockSearch(
  { onPick }: { onPick: (symbol: string) => void },
) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<SaudiCompany[]>([]);
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const wrapRef = React.useRef<HTMLDivElement | null>(null);

  const close = () => { setOpen(false); setQ(""); setHits([]); };

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
            if (e.key === "Enter" && (hits[0] || q)) pick(hits[0]?.symbol || q);
            if (e.key === "Escape") close();
          }} />
      </div>

      {open && hits.length > 0 && (
        <div className="sp-menu absolute z-30 top-full mt-1.5 end-0 rounded-xl overflow-hidden shadow-2xl"
             style={{ width: 280, maxHeight: 300, overflowY: "auto" }}>
          {hits.slice(0, 40).map(c => (
            <button key={c.symbol} type="button" onClick={() => pick(c.symbol)}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 text-start hover:panel transition-colors">
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
