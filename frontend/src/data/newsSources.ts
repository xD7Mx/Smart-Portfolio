// قائمة مصادر الأخبار الرسمية المعتمدة — mirrors the backend's canonical
// registry (backend/app/data/news_sources.py). Each outlet carries its REAL
// domain; the logo is resolved from that domain (Clearbit → favicon chain in
// SourceLogo) — the same convention already used for company logos, never an
// invented image URL. One policy list, injected, no chaos.
// `logo` (optional): an explicit logo image URL for the outlet. When present it
// overrides the domain-derived logo (Clearbit/favicon) in SourceLogo. Use it for
// outlets whose domain logo is missing/wrong.
export interface NewsSource { name_ar: string; aliases: string[]; domain: string; logo?: string }

export const NEWS_SOURCES: NewsSource[] = [
  { name_ar: "أرقام", aliases: ["أرقام","Argaam","argaam"], domain: "argaam.com" },
  { name_ar: "مباشر", aliases: ["مباشر","معلومات مباشر","Mubasher"], domain: "mubasher.info" },
  { name_ar: "معلومات مباشر", aliases: ["Mubasher Info"], domain: "english.mubasher.info" },
  { name_ar: "مال", aliases: ["مال","Maaal","صحيفة مال"], domain: "maaal.com" },
  { name_ar: "الاقتصادية", aliases: ["الاقتصادية","Aleqt","صحيفة الاقتصادية"], domain: "aleqt.com", logo: "https://upload.wikimedia.org/wikipedia/ar/thumb/2/25/%D8%B4%D8%B9%D8%A7%D8%B1_%D8%B5%D8%AD%D9%8A%D9%81%D8%A9_%D8%A7%D9%84%D8%A7%D9%82%D8%AA%D8%B5%D8%A7%D8%AF%D9%8A%D8%A9.svg/960px-%D8%B4%D8%B9%D8%A7%D8%B1_%D8%B5%D8%AD%D9%8A%D9%81%D8%A9_%D8%A7%D9%84%D8%A7%D9%82%D8%AA%D8%B5%D8%A7%D8%AF%D9%8A%D8%A9.svg.png" },
  { name_ar: "الشرق بلومبيرغ", aliases: ["الشرق بلومبيرغ","اقتصاد الشرق","Asharq Business"], domain: "asharqbusiness.com", logo: "https://www.jobzaty.com/company_logos/mjmoaa-alshrk-blombyrgh-alekhbary-1621374114-6.png" },
  { name_ar: "CNBC عربية", aliases: ["CNBC عربية","CNBC Arabia","سي إن بي سي عربية"], domain: "cnbcarabia.com" },
  { name_ar: "فوربس الشرق الأوسط", aliases: ["فوربس الشرق الأوسط","Forbes Middle East"], domain: "forbesmiddleeast.com" },
  { name_ar: "زاوية", aliases: ["زاوية","Zawya"], domain: "zawya.com" },
  { name_ar: "رويترز", aliases: ["رويترز","Reuters"], domain: "reuters.com" },
  { name_ar: "بلومبيرغ", aliases: ["بلومبيرغ","Bloomberg"], domain: "bloomberg.com" },
  { name_ar: "الرياض", aliases: ["الرياض","صحيفة الرياض","Alriyadh"], domain: "alriyadh.com" },
  { name_ar: "عكاظ", aliases: ["عكاظ","Okaz"], domain: "okaz.com.sa" },
  { name_ar: "اليوم", aliases: ["اليوم","صحيفة اليوم","Alyaum"], domain: "alyaum.com" },
  { name_ar: "الجزيرة (صحيفة سعودية)", aliases: ["الجزيرة","صحيفة الجزيرة","Al-Jazirah"], domain: "al-jazirah.com" },
  { name_ar: "الوطن", aliases: ["الوطن","صحيفة الوطن"], domain: "alwatan.com.sa" },
  { name_ar: "المدينة", aliases: ["المدينة","صحيفة المدينة"], domain: "al-madina.com" },
  { name_ar: "البلاد", aliases: ["البلاد","صحيفة البلاد"], domain: "albiladdaily.com" },
  { name_ar: "سبق", aliases: ["سبق","صحيفة سبق","Sabq"], domain: "sabq.org" },
  { name_ar: "عاجل", aliases: ["عاجل","Ajel"], domain: "ajel.sa" },
  { name_ar: "المواطن", aliases: ["المواطن","Almowaten"], domain: "almowaten.net" },
  { name_ar: "صحيفة مكة", aliases: ["مكة","صحيفة مكة","Makkah"], domain: "makkahnp.com" },
  { name_ar: "عرب نيوز", aliases: ["Arab News","عرب نيوز"], domain: "arabnews.com" },
  { name_ar: "سعودي غازيت", aliases: ["Saudi Gazette","أخبار السعودية"], domain: "saudigazette.com.sa" },
  { name_ar: "الوئام", aliases: ["الوئام","Alweeam"], domain: "alweeam.com.sa" },
  { name_ar: "العربية", aliases: ["العربية","Al Arabiya","العربية نت","أسواق العربية"], domain: "alarabiya.net" },
  { name_ar: "الشرق للأخبار", aliases: ["الشرق","الشرق للأخبار","Asharq News"], domain: "asharq.com" },
  { name_ar: "الإخبارية", aliases: ["الإخبارية","Al Ekhbariya"], domain: "alekhbariya.net" },
  { name_ar: "هيئة الإذاعة والتلفزيون", aliases: ["هيئة الإذاعة والتلفزيون","SBA"], domain: "sba.sa" },
  { name_ar: "واس (وكالة الأنباء السعودية)", aliases: ["واس","SPA","وكالة الأنباء السعودية"], domain: "spa.gov.sa" },
  { name_ar: "تداول السعودية", aliases: ["تداول","Tadawul","Saudi Exchange","السوق المالية السعودية"], domain: "saudiexchange.sa" },
  { name_ar: "هيئة السوق المالية (CMA)", aliases: ["هيئة السوق المالية","CMA"], domain: "cma.org.sa" },
  { name_ar: "البنك المركزي السعودي (ساما)", aliases: ["ساما","SAMA","البنك المركزي السعودي"], domain: "sama.gov.sa" },
  { name_ar: "وزارة المالية", aliases: ["وزارة المالية","Ministry of Finance"], domain: "mof.gov.sa" },
  { name_ar: "وزارة الاقتصاد والتخطيط", aliases: ["وزارة الاقتصاد والتخطيط","MEP"], domain: "mep.gov.sa" },
  { name_ar: "هيئة الزكاة والضريبة والجمارك", aliases: ["زاتكا","ZATCA"], domain: "zatca.gov.sa" },
  { name_ar: "مركز إيداع (إيداع)", aliases: ["إيداع","Edaa","مركز إيداع"], domain: "edaa.com.sa" },
  { name_ar: "الهيئة العامة للإحصاء", aliases: ["الهيئة العامة للإحصاء","GASTAT"], domain: "stats.gov.sa" },
  { name_ar: "صندوق الاستثمارات العامة (PIF)", aliases: ["صندوق الاستثمارات العامة","PIF"], domain: "pif.gov.sa" },
  { name_ar: "أرامكو السعودية", aliases: ["أرامكو","Aramco","Saudi Aramco"], domain: "aramco.com" },
  { name_ar: "وزارة الطاقة", aliases: ["وزارة الطاقة"], domain: "moenergy.gov.sa" },
  { name_ar: "الهيئة العامة للمنافسة", aliases: ["الهيئة العامة للمنافسة","GAC"], domain: "gac.gov.sa" },
  { name_ar: "المركز الوطني لإدارة الدين", aliases: ["المركز الوطني لإدارة الدين","NDMC"], domain: "ndmc.gov.sa" },
  { name_ar: "وزارة الاستثمار", aliases: ["وزارة الاستثمار","MISA"], domain: "misa.gov.sa" },
  { name_ar: "وزارة التجارة", aliases: ["وزارة التجارة"], domain: "mc.gov.sa" },
  { name_ar: "منشآت", aliases: ["منشآت","Monshaat"], domain: "monshaat.gov.sa" },
  { name_ar: "صندوق التنمية الصناعية", aliases: ["صندوق التنمية الصناعية","SIDF"], domain: "sidf.gov.sa" },
  { name_ar: "صندوق التنمية الوطني", aliases: ["صندوق التنمية الوطني","NDF"], domain: "ndf.gov.sa" },
  { name_ar: "هيئة الاتصالات والفضاء والتقنية", aliases: ["CST","هيئة الاتصالات"], domain: "cst.gov.sa" },
  { name_ar: "التأمينات الاجتماعية (GOSI)", aliases: ["التأمينات الاجتماعية","GOSI"], domain: "gosi.gov.sa" },
  { name_ar: "رؤية 2030", aliases: ["رؤية 2030","Vision 2030"], domain: "vision2030.gov.sa" },
  { name_ar: "نيوم", aliases: ["نيوم","NEOM"], domain: "neom.com" },
  { name_ar: "روشن", aliases: ["روشن","ROSHN"], domain: "roshn.sa" },
  { name_ar: "مدن (المدن الصناعية)", aliases: ["مدن","MODON"], domain: "modon.gov.sa" },
  { name_ar: "الطيران المدني (GACA)", aliases: ["الطيران المدني","GACA"], domain: "gaca.gov.sa" },
  { name_ar: "الهيئة السعودية للمحاسبين (SOCPA)", aliases: ["SOCPA","المحاسبين القانونيين"], domain: "socpa.org.sa" },
  { name_ar: "مجلس الغرف السعودية", aliases: ["مجلس الغرف السعودية"], domain: "csc.org.sa" },
  { name_ar: "الصادرات السعودية", aliases: ["الصادرات السعودية"], domain: "saudiexports.sa" },
  { name_ar: "الراجحي المالية", aliases: ["الراجحي المالية","Al Rajhi Capital"], domain: "alrajhi-capital.com" },
  { name_ar: "الأهلي المالية (SNB Capital)", aliases: ["الأهلي المالية","SNB Capital","الأهلي كابيتال"], domain: "snbcapital.com" },
  { name_ar: "الجزيرة كابيتال", aliases: ["الجزيرة كابيتال","Aljazira Capital"], domain: "aljaziracapital.com.sa" },
  { name_ar: "البلاد المالية", aliases: ["البلاد المالية","Albilad Capital"], domain: "albilad-capital.com" },
  { name_ar: "الرياض المالية", aliases: ["الرياض المالية","Riyad Capital"], domain: "riyadcapital.com" },
  { name_ar: "دراية المالية", aliases: ["دراية","Derayah"], domain: "derayah.com" },
  { name_ar: "السعودي الفرنسي كابيتال", aliases: ["السعودي الفرنسي كابيتال","Saudi Fransi Capital"], domain: "sfc.sa" },
  { name_ar: "جدوى للاستثمار", aliases: ["جدوى","Jadwa"], domain: "jadwa.com" },
  { name_ar: "يقين المالية", aliases: ["يقين","Yaqeen Capital"], domain: "yaqeen.sa" },
  { name_ar: "الاستثمار كابيتال", aliases: ["الاستثمار كابيتال","Alistithmar Capital"], domain: "icap.com.sa" },
  { name_ar: "الإنماء للاستثمار", aliases: ["الإنماء للاستثمار","Alinma Investment"], domain: "alinmainvestment.com" },
  { name_ar: "HSBC السعودية", aliases: ["HSBC Saudi"], domain: "hsbcsaudi.com" },
  { name_ar: "أصول وبخيت للاستثمار", aliases: ["أصول وبخيت","Osool & Bakheet"], domain: "osoolbakheet.com.sa" },
  { name_ar: "مركز الملك فيصل للبحوث", aliases: ["King Faisal Center","KFCRIS"], domain: "kfcris.com" },
  { name_ar: "تريدينغ فيو", aliases: ["TradingView","تريدينغ فيو"], domain: "tradingview.com" },
  { name_ar: "Investing عربي", aliases: ["Investing","انفستنج","Investing.com"], domain: "sa.investing.com" },
  { name_ar: "ياهو فاينانس", aliases: ["Yahoo Finance","ياهو فاينانس"], domain: "finance.yahoo.com" },
  { name_ar: "سهم كابيتال", aliases: ["Sahm Capital","سهم"], domain: "sahmcapital.com" },
];

const ALIAS_INDEX = new Map<string, NewsSource>();
for (const src of NEWS_SOURCES) for (const a of src.aliases) ALIAS_INDEX.set(a, src);

/** Canonical outlet entry for a feed's source label — null if not approved. */
export function matchSource(source?: string | null): NewsSource | null {
  if (!source) return null;
  const s = source.trim();
  const exact = ALIAS_INDEX.get(s);
  if (exact) return exact;
  for (const [alias, entry] of ALIAS_INDEX) {
    if (alias && s.includes(alias)) return entry;
  }
  return null;
}
