/* ══ المؤشّراتُ والسلعُ في البحث ══ (‏D812 — المالك 2026-11-24)
   «علامةُ البحث داخل الإطارات لا تدعم المؤشّرات — سواءٌ كتبتُ تاسي أو غيره يجب أن تدعمها، وأيضاً برنت والذهب وغيرها. مربّعُ البحث سبيلُنا
   للوصول إلى الرسم المراد، فيجب دعمُ السوق السعوديّ والأمريكيّ والمؤشّرات أيضاً داخل كلّ إطار».
   بحثُ الخادم يعرف الأسهمَ برموزها اللاتينية، ودليلُ «تداول» يعرف الشركاتِ السعودية — ولا أحدَ منهما يعرف «تاسي» ولا «الذهب» ولا «برنت».
   فهذه خريطةُ أسماءٍ لا أسعار: الرمزُ رمزُ المصدر نفسِه (ياهو) الذي يرسم منه التطبيقُ تاسي وبرنت والذهب وبتكوين في «المؤشرات» اليوم؛
   والأسماءُ العربيةُ والإنجليزيةُ الدارجةُ تدلّ عليه. */

export type MarketItem = { symbol: string; name: string; kind: string; al: string[] };

export const MARKETS: MarketItem[] = [
  { symbol: "^TASI.SR", name: "تاسي — المؤشّر العام", kind: "مؤشّرٌ سعوديّ", al: ["تاسي", "تاسى", "المؤشر العام", "مؤشر السوق", "السوق السعودي", "tasi"] },
  { symbol: "^GSPC", name: "S&P 500", kind: "مؤشّرٌ أمريكيّ", al: ["اس اند بي", "اس آند بي", "اس اند بي 500", "s&p", "s&p 500", "sp500", "spx", "gspc"] },
  { symbol: "^IXIC", name: "ناسداك المركّب", kind: "مؤشّرٌ أمريكيّ", al: ["ناسداك", "نازداك", "ناسداك المركب", "nasdaq", "ixic"] },
  { symbol: "^NDX", name: "ناسداك 100", kind: "مؤشّرٌ أمريكيّ", al: ["ناسداك 100", "nasdaq 100", "ndx"] },
  { symbol: "^DJI", name: "داو جونز", kind: "مؤشّرٌ أمريكيّ", al: ["داو", "داو جونز", "dow", "dow jones", "dji"] },
  { symbol: "^RUT", name: "راسل 2000", kind: "مؤشّرٌ أمريكيّ", al: ["راسل", "راسل 2000", "russell", "russell 2000", "rut"] },
  { symbol: "^VIX", name: "مؤشّر التقلّب VIX", kind: "مؤشّرٌ أمريكيّ", al: ["فيكس", "مؤشر الخوف", "مؤشر التقلب", "التقلب", "vix"] },
  { symbol: "BZ=F", name: "خام برنت", kind: "سلعة", al: ["برنت", "خام برنت", "النفط", "نفط", "brent", "oil"] },
  { symbol: "CL=F", name: "خام غرب تكساس", kind: "سلعة", al: ["غرب تكساس", "نفط تكساس", "الخام الامريكي", "wti", "crude"] },
  { symbol: "GC=F", name: "الذهب", kind: "سلعة", al: ["الذهب", "ذهب", "gold", "xau"] },
  { symbol: "SI=F", name: "الفضّة", kind: "سلعة", al: ["الفضه", "فضه", "silver", "xag"] },
  { symbol: "NG=F", name: "الغاز الطبيعي", kind: "سلعة", al: ["الغاز", "غاز", "الغاز الطبيعي", "natural gas", "natgas"] },
  { symbol: "HG=F", name: "النحاس", kind: "سلعة", al: ["النحاس", "نحاس", "copper"] },
  { symbol: "BTC-USD", name: "بتكوين", kind: "عملةٌ رقمية", al: ["بتكوين", "بيتكوين", "bitcoin", "btc"] },
  { symbol: "ETH-USD", name: "إيثريوم", kind: "عملةٌ رقمية", al: ["ايثريوم", "ايثيريوم", "اثيريوم", "ethereum", "eth"] },
  { symbol: "DX-Y.NYB", name: "مؤشّر الدولار", kind: "عملة", al: ["الدولار", "مؤشر الدولار", "دولار", "dxy", "dollar index"] },
  { symbol: "^TNX", name: "عائدُ السندات الأمريكية 10 سنوات", kind: "عائد", al: ["السندات", "عائد السندات", "سندات", "tnx", "10y", "treasury"] },
];

/** الاسمُ العربيُّ القصيرُ للعنوان (رأسُ الشاشة) — «تاسي» لا «تاسي — المؤشّر العام» */
export const MARKET_NAME: Record<string, string> = Object.fromEntries(MARKETS.map(m => [m.symbol, m.name.split(" — ")[0]]));

const norm = (t: string) => t.toLowerCase().replace(/[إأآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
  .replace(/[ً-ْـ]/g, "").replace(/\s+/g, " ").trim();

/** ما يوافق المكتوبَ اسماً (بداية اسمٍ دارج، أو داخلَه من ثلاثة أحرف) أو رمزاً (‏GC · ^GS · BTC) — حرفان على الأقلّ */
export function searchMarkets(q: string): MarketItem[] {
  const t = norm(q), T = q.trim().toUpperCase();
  if (t.length < 2) return [];
  return MARKETS.filter(m => m.al.some(a => { const n = norm(a); return n.startsWith(t) || (t.length >= 3 && n.includes(t)); })
    || m.symbol.replace(/^\^/, "").startsWith(T.replace(/^\^/, "")));
}
