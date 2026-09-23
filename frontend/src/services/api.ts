import axios from "axios";
import type { APIResponse } from "../types";
import { useAuthStore, getToken } from "../store/authStore";
import { getActivePortfolioId, getWealthUnified } from "../store/portfolioStore";

const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

// Back-compat alias — the auth store (reactive, drives the UI) is now the
// source of truth; this just exposes the same read/write for non-React code.
export const authToken = {
  get: getToken,
  set: (t: string) => useAuthStore.getState().login(t),
  clear: () => useAuthStore.getState().logout(),
};

/* مُعرِّف جهازٍ ثابت يُولَّد مرّة ويبقى في هذا المتصفّح.
   سببه: بدونه كان كل دخولٍ من نفس الجوّال يفتح صفّاً جديداً في «الجلسات
   النشطة» — عشرة صفوف «آيفون · Safari» لجهازٍ واحد، وعشرة توكنات حيّة.
   وسم الجهاز من User-Agent لا يكفي للتمييز: جهازان متطابقان خلف نفس
   الشبكة يتشابهان تماماً. هذا رقمٌ عشوائي لا يحمل أي معلومة عنك. */
const DEVICE_KEY = "sp_device_id";
function deviceId(): string {
  try {
    let v = localStorage.getItem(DEVICE_KEY);
    if (!v) {
      v = (crypto?.randomUUID?.() || Math.random().toString(36).slice(2) + Date.now().toString(36));
      localStorage.setItem(DEVICE_KEY, v);
    }
    return v;
  } catch { return ""; }
}

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// ── Interceptors ─────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const did = deviceId();
  if (did) config.headers["X-Device-Id"] = did;
  // المحفظة النشطة — تُعزَل بياناتها في الخادم عبر هذه الترويسة.
  const pid = getActivePortfolioId();
  if (pid) config.headers["X-Portfolio-Id"] = pid;
  // توحيد الثروة: قراءة مُجمَّعة عبر كل المحافظ (الإدخال يبقى للمحفظة النشطة).
  if (getWealthUnified()) config.headers["X-Portfolio-Aggregate"] = "1";
  // للرفع بـFormData (استعادة النسخة الاحتياطية): نزيل Content-Type الافتراضي
  // (application/json) كي يضبطه المتصفح تلقائياً إلى multipart مع الـboundary
  // الصحيح — بدونه لا يستطيع الخادم قراءة الملف وتفشل الاستعادة.
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete (config.headers as any)["Content-Type"];
    delete (config.headers as any)["content-type"];
  }
  return config;
});

// Some upstream sources (news, external market data) occasionally contain
// Eastern Arabic-Indic digits (٠-٩) or Extended Arabic-Indic (۰-۹) inside
// text fields — the site's own numbers are always formatted with explicit
// Latin-digit locales, but we don't control third-party text content, so we
// normalize every string in every response here, once, at the source.
const EASTERN_DIGITS_TEST = /[٠-٩۰-۹]/;
const EASTERN_DIGITS_ALL = /[٠-٩۰-۹]/g;
const toLatinDigits = (s: string) =>
  s.replace(EASTERN_DIGITS_ALL, (d) => {
    const code = d.charCodeAt(0);
    const base = code >= 0x06f0 ? 0x06f0 : 0x0660;
    return String(code - base);
  });
const normalizeDigits = (data: any): any => {
  if (typeof data === "string") return EASTERN_DIGITS_TEST.test(data) ? toLatinDigits(data) : data;
  if (Array.isArray(data)) return data.map(normalizeDigits);
  if (data && typeof data === "object") {
    for (const k of Object.keys(data)) data[k] = normalizeDigits(data[k]);
    return data;
  }
  return data;
};

api.interceptors.response.use(
  (res) => {
    if (res.data) res.data = normalizeDigits(res.data);
    return res;
  },
  (err) => {
    console.error("API Error:", err?.response?.data?.message || err.message);
    if (err?.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login: (password: string) => api.post<APIResponse>("/auth/login", { password }),
  logout: () => api.post<APIResponse>("/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    api.post<APIResponse>("/auth/change-password", { current_password, new_password }),
  revokeAll: () => api.post<APIResponse>("/auth/revoke-all"),
  sessions: () => api.get<APIResponse>("/auth/sessions"),
  revokeSession: (jti: string) => api.post<APIResponse>(`/auth/sessions/${jti}/revoke`),
  revokeOthers: () => api.post<APIResponse>("/auth/sessions/revoke-others"),
};

// ── Portfolio ─────────────────────────────────────────────────
export const portfolioApi = {
  get:        () => api.get<APIResponse>("/holdings"),
  summary:    () => api.get<APIResponse>("/portfolio/summary"),
  health:     () => api.get<APIResponse>("/portfolio/health"),
  roi:        () => api.get<APIResponse>("/portfolio/roi"),
  income:     () => api.get<APIResponse>("/portfolio/income"),
  statistics: () => api.get<APIResponse>("/portfolio/statistics"),
  metrics:    () => api.get<APIResponse>("/portfolio/metrics"),
  performance: () => api.get<APIResponse>("/portfolio/performance"),
  integrity:   () => api.get<APIResponse>("/portfolio/integrity"),
  history:    (days = 365) => api.get<APIResponse>(`/portfolio/history?days=${days}`),
  snapshot:   () => api.post<APIResponse>("/portfolio/snapshot"),
  governance: () => api.get<APIResponse>("/portfolio/governance"),
  governanceMarket: () => api.get<APIResponse>("/portfolio/governance-market"),
  sectorMap: () => api.get<APIResponse>("/portfolio/sector-map"),
  governanceV2: (symbol: string) => api.get<APIResponse>(`/portfolio/governance-v2/${symbol}`),
};

// ── Companies ─────────────────────────────────────────────────
export const companiesApi = {
  list:   ()          => api.get<APIResponse>("/companies"),
  get:    (id: number) => api.get<APIResponse>(`/companies/${id}`),
  add:    (data: any) => api.post<APIResponse>("/companies", data),
  update: (id: number, data: any) => api.put<APIResponse>(`/companies/${id}`, data),
  remove: (id: number) => api.delete<APIResponse>(`/companies/${id}`),
  syncSharia: () => api.post<APIResponse>("/companies/sync-sharia"),
  resolveSharia: (id: number) => api.post<APIResponse>(`/companies/${id}/resolve-sharia`),
  directory: () => api.get<APIResponse>("/companies/directory"),
  // نبذة النشاط والإدارة التنفيذية — من Yahoo حصراً
  profile: (id: number) => api.get<APIResponse>(`/companies/${id}/profile`),
  // النبذةُ نفسُها لورقةٍ لا تملك صفّاً في المحفظة (D209).
  profileBySymbol: (symbol: string) =>
    api.get<APIResponse>(`/companies/by-symbol/${symbol.replace(".SR", "")}/profile`),
  saveProfile: (id: number, data: { description?: string | null }) =>
    api.put<APIResponse>(`/companies/${id}/profile`, data),
};

// ── Holdings ──────────────────────────────────────────────────
export const holdingsApi = {
  production: (companyId: number) => api.get<APIResponse>(`/holdings/${companyId}/production`),
  list: () => api.get<APIResponse>("/holdings"),
  get:  (companyId: number) => api.get<APIResponse>(`/holdings/${companyId}`),
  // ترتيب العرض الذي يختاره المالك — مصدرٌ واحد تتبعه كل البطاقات.
  setOrder: (order: number[]) => api.put<APIResponse>("/holdings/order", { order }),
  update: (companyId: number, data: { quantity?: number; average_cost?: number }) =>
    api.patch<APIResponse>(`/holdings/${companyId}`, data),
};

// ── Transactions ──────────────────────────────────────────────
export const transactionsApi = {
  /* الترشيح بالشركة على الخادم: الحدّ كان ١٠٠ للمحفظة كلّها ثم تُرشّح
     الواجهة، فتختفي عمليات الشركة القديمة بلا أثر متى تجاوز المجموع المئة. */
  list:   (companyId?: number, limit = 500) =>
    api.get<APIResponse>("/transactions" + (companyId ? `?company_id=${companyId}&limit=${limit}` : `?limit=${limit}`)),
  add:    (data: any) => api.post<APIResponse>("/transactions", data),
  get:    (id: number) => api.get<APIResponse>(`/transactions/${id}`),
  remove: (id: number) => api.delete<APIResponse>(`/transactions/${id}`),
  // مراجعة الأوسمة: كشف ما يستحيل حسابياً، وإزالته بقرار المالك وحده.
  tagAudit: () => api.get<APIResponse>("/transactions/tag-audit"),
  untag:  (ids: number[]) => api.post<APIResponse>("/transactions/untag", { ids }),
  // تحرير كامل للعملية عدا نوعها. الخادم يعكس أثر النقد القديم ويطبّق الجديد،
  // ويعيد بناء الحيازة من إعادة تشغيل السجل — فلا يفسد رصيدٌ ولا كمية.
  patch:  (id: number, data: {
    quantity?: number; price?: number; fees?: number; amount?: number;
    executed_at?: string; notes?: string;
    funding_source?: string; set_funding_source?: boolean;
  }) => api.patch<APIResponse>(`/transactions/${id}`, data),
};

// ── Installments ──────────────────────────────────────────────
export const installmentsApi = {
  list:    ()                          => api.get<APIResponse>("/installments"),
  add:     (data: any)                 => api.post<APIResponse>("/installments", data),
  update:  (id: number, status: string) => api.patch<APIResponse>(`/installments/${id}?status=${status}`),
  nearest: ()                          => api.get<APIResponse>("/installments/nearest"),
};

// ── Cash ──────────────────────────────────────────────────────
export const cashApi = {
  get:     () => api.get<APIResponse>("/cash"),
  balance: () => api.get<APIResponse>("/cash"),
  history: (limit = 30) => api.get<APIResponse>(`/cash/history?limit=${limit}`),
  deposit: (data: any) => api.post<APIResponse>("/cash/deposit", data),
  withdraw:(data: any) => api.post<APIResponse>("/cash/withdraw", data),
  removeLedger: (id: number) => api.delete<APIResponse>(`/cash/ledger/${id}`),
};

// ── Dividends ─────────────────────────────────────────────────
export const dividendsApi = {
  list:   () => api.get<APIResponse>("/dividends"),
  add:    (data: any) => api.post<APIResponse>("/dividends", data),
  update: (id: number, data: { dividend_per_share?: number; shares_at_time?: number; payment_date?: string }) =>
    api.patch<APIResponse>(`/dividends/${id}`, data),
  remove: (id: number) => api.delete<APIResponse>(`/dividends/${id}`),
};

// ── Bonus Shares ──────────────────────────────────────────────
export const bonusApi = {
  list: () => api.get<APIResponse>("/bonus"),
  add:  (data: any) => api.post<APIResponse>("/bonus", data),
};

// ── Goals ─────────────────────────────────────────────────────
export const goalsApi = {
  list:     () => api.get<APIResponse>("/goals"),
  add:      (data: any) => api.post<APIResponse>("/goals", data),
  update:   (id: number, currentValue: number) => api.patch<APIResponse>(`/goals/${id}?current_value=${currentValue}`),
  remove:   (id: number) => api.delete<APIResponse>(`/goals/${id}`),
  progress: () => api.get<APIResponse>("/goals/progress"),
  builtin:  () => api.get<APIResponse>("/goals/builtin"),
  builtinConfig: () => api.get<APIResponse>("/goals/builtin-config"),
  saveBuiltinConfig: (data: any) => api.post<APIResponse>("/goals/builtin-config", data),
  incomeHistory: () => api.get<APIResponse>("/goals/income-history"),
  incomeTimeline: () => api.get<APIResponse>("/goals/income-timeline"),
};

// ── Market ────────────────────────────────────────────────────
export const marketApi = {
  directory: () => api.get<APIResponse>("/market/directory"),
  overview: () => api.get<APIResponse>("/market/overview"),
  movers:   () => api.get<APIResponse>("/market/movers"),
  news:     (lang: string = "ar") => api.get<APIResponse>(`/market/news?lang=${lang}`),
  portfolioNews: () => api.get<APIResponse>("/market/news", { params: { portfolio_only: true } }),
  resolveNewsUrl: (u: string) => api.get<APIResponse>("/market/news/resolve", { params: { u } }),
  eventDetail: (id: string) => api.get<APIResponse>(`/market/event-detail/${id}`),
  argaamIds: () => api.get<APIResponse>("/market/argaam-ids"),
  summary:  () => api.get<APIResponse>("/market/summary"),
  economicNews: () => api.get<APIResponse>("/market/economic-news"),
  feedstock: () => api.get<APIResponse>("/market/feedstock"),
  events:   () => api.get<APIResponse>("/market/events"),
  eventsMarket: () => api.get<APIResponse>("/market/events-market"),
  companyEvents: (symbol: string, name?: string) => api.get<APIResponse>(`/market/events/${symbol}`, { params: name ? { name } : undefined }),
  results:  () => api.get<APIResponse>("/market/results"),
  company:  (symbol: string) => api.get<APIResponse>(`/market/company/${symbol}`),
  // عمقُ السوق: مستوًى واحدٌ من لقطة «تداول» (D272).
  depth:    (symbol: string) => api.get<APIResponse>(`/market/depth/${symbol}`),
  // الصفقاتُ الخاصة — كلُّ السوق أو لشركةٍ (D288).
  specialDeals: (days = 30, symbol?: string) => api.get<APIResponse>(
    `/market/special-deals?days=${days}` + (symbol ? `&symbol=${symbol}` : "")),
  history:  (symbol: string, range = "3mo") => api.get<APIResponse>(`/market/history/${encodeURIComponent(symbol)}?range=${range}`),
  recommendations: (symbol: string) => api.get<APIResponse>(`/market/recommendations/${symbol}`),
  financials: (symbol: string, period: "annual" | "quarterly" = "annual") =>
    api.get<APIResponse>(`/market/financials/${symbol}?period=${period}`),
  ownership:  (symbol: string) => api.get<APIResponse>(`/market/ownership/${symbol}`),
  dividends:  (symbol: string) => api.get<APIResponse>(`/market/dividends/${symbol}`),
  sectors:  () => api.get<APIResponse>("/market/sectors"),
  screener:   () => api.get<APIResponse>("/market/screener"),
  // حاسبةُ الاكتتاب — مضاعفاتُ القطاعات، والتقييمُ بالمحرّك نفسِه (D231).
  ipoSectors: () => api.get<APIResponse>("/market/ipo-sectors"),
  ipoValue: (p: { sector: string; net_profit: number; equity: number; shares: number; offer_price?: number }) =>
    api.get<APIResponse>("/market/ipo-value", { params: p }),
  watchlist:  (groupId?: number | string) => api.get<APIResponse>("/market/watchlist", { params: groupId ? { group_id: groupId } : undefined }),
  watchAdd:   (symbol: string, name?: string, groupId?: number | string) => api.post<APIResponse>("/market/watchlist", { symbol, name, group_id: groupId }),
  watchRemove: (symbol: string, groupId?: number | string) => api.delete<APIResponse>(`/market/watchlist/${symbol}`, { params: groupId ? { group_id: groupId } : undefined }),
  watchMembership: (symbol: string) => api.get<APIResponse>("/market/watchlist/membership", { params: { symbol } }),
  watchGroups: () => api.get<APIResponse>("/market/watchlist/groups"),
  watchGroupCreate: (body: { name: string; color?: string }) => api.post<APIResponse>("/market/watchlist/groups", body),
  watchGroupUpdate: (id: number | string, body: { name?: string; color?: string }) => api.patch<APIResponse>(`/market/watchlist/groups/${id}`, body),
  watchGroupRemove: (id: number | string) => api.delete<APIResponse>(`/market/watchlist/groups/${id}`),
};

// ── Portfolios (تعدّد المحافظ) ────────────────────────────────
export const portfoliosApi = {
  list:   () => api.get<APIResponse>("/portfolios"),
  create: (body: { name: string; color?: string; include_in_aggregate?: boolean }) =>
    api.post<APIResponse>("/portfolios", body),
  update: (id: number | string, body: { name?: string; color?: string; include_in_aggregate?: boolean }) =>
    api.patch<APIResponse>(`/portfolios/${id}`, body),
  setDefault: (id: number | string) => api.post<APIResponse>(`/portfolios/${id}/set-default`),
  remove: (id: number | string) => api.delete<APIResponse>(`/portfolios/${id}`),
};

// ── AI ────────────────────────────────────────────────────────
export const aiApi = {
  status:      () => api.get<APIResponse>("/ai/status"),
  /* سؤال المساعد قد يمرّ بالنموذج التوليدي، وهو أبطأ من أي نداءٍ آخر في
     التطبيق. مهلة الثلاثين ثانية العامة كانت تقطع الاتصال والخادم ما زال
     يعمل، فتظهر «تعذّر الاتصال بالخادم» والخادم بخير. ميزانية الخادم
     للنموذج عشرون ثانية، وهذه ستّون — هامشٌ يكفي ولا يترك المستخدم معلّقاً. */
  chat:        (message: string, history: any[] = []) =>
    api.post<APIResponse>("/ai/chat", { message, history }, { timeout: 60000 }),
  run:         () => api.post<APIResponse>("/ai/run"),
  report:      () => api.get<APIResponse>("/ai/report"),
  evaluation:  () => api.get<APIResponse>("/ai/evaluation"),
  opportunities:() => api.get<APIResponse>("/ai/opportunities"),
  risk:        () => api.get<APIResponse>("/ai/risk"),
  fullReport:  () => api.get<APIResponse>("/ai/full-report"),
  portfolioInsight: () => api.get<APIResponse>("/ai/portfolio-insight"),
  stockOpinion: (symbol: string, name?: string) => api.get<APIResponse>(`/ai/stock-opinion/${symbol}`, { params: name ? { name } : undefined }),
};

// ── Notifications ─────────────────────────────────────────────
export const notificationsApi = {
  list:      () => api.get<APIResponse>("/notifications"),
  read:      (id: number) => api.patch<APIResponse>(`/notifications/${id}/read`),
  delete:    (id: number) => api.delete<APIResponse>(`/notifications/${id}`),
  readAll:   () => api.patch<APIResponse>("/notifications/read-all"),
  deleteRead:() => api.delete<APIResponse>("/notifications/read"),
  deleteAll: () => api.delete<APIResponse>("/notifications"),
};

// ── Reports ───────────────────────────────────────────────────
export const reportsApi = {
  list:     () => api.get<APIResponse>("/reports"),
  generate: (type: string) => api.post<APIResponse>(`/reports/generate?report_type=${type}`),
  get:      (id: number) => api.get<APIResponse>(`/reports/${id}`),
  remove:   (id: number) => api.delete<APIResponse>(`/reports/${id}`),
};

// ── Library (المكتبة) ─────────────────────────────────────────
// ملف الـPDF محميّ بالتوكن، فلا يصلح تمريره مباشرةً في <iframe>/<a>؛ نجلبه
// blob عبر axios (يضيف الـAuthorization) ونصنع Object URL للمعاينة/التحميل.
export const libraryApi = {
  list:    () => api.get<APIResponse>("/library"),
  insight: (id: number, slot = 0) => api.get<APIResponse>(`/library/${id}/insight?slot=${slot}`),
  reader:  (id: number) => api.get<APIResponse>(`/library/${id}/reader`),
  fileBlob: (id: number, download = false) =>
    api.get(`/library/${id}/file${download ? "?download=true" : ""}`, { responseType: "blob" }),
  coverBlob: (id: number, ver = 0) => api.get(`/library/${id}/cover?v=${ver}`, { responseType: "blob" }),
  pageImage: (id: number, n: number, scale = 2) =>
    api.get(`/library/${id}/page/${n}?scale=${scale}`, { responseType: "blob" }),
  setCover: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<APIResponse>(`/library/${id}/cover`, form, { timeout: 60000 });
  },
  upload:  (file: File, title: string, author: string, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    form.append("author", author);
    // مهلة واسعة: الكتب المصوّرة تمرّ بـOCR عربي عند الرفع (مرّة واحدة) وقد يطول.
    return api.post<APIResponse>("/library/upload", form, {
      timeout: 600000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
  },
  remove:  (id: number) => api.delete<APIResponse>(`/library/${id}`),
  reorder: (ids: number[]) => api.post<APIResponse>("/library/reorder", { ids }),
};

// ── Settings ──────────────────────────────────────────────────
export const settingsApi = {
  get:       () => api.get<APIResponse>("/settings"),
  ai:        () => api.get<APIResponse>("/settings/ai"),
  telegram:  () => api.get<APIResponse>("/settings/telegram"),
  telegramTest: () => api.post<APIResponse>("/settings/telegram/test"),
  providers: () => api.get<APIResponse>("/settings/providers"),
  system:    () => api.get<APIResponse>("/settings/system"),
  integrations: (refresh = false) => api.get<APIResponse>("/settings/integrations" + (refresh ? "?refresh=true" : "")),
  refreshPortfolioData: () => api.post<APIResponse>("/settings/refresh-portfolio-data"),
  serverTime: () => api.get<APIResponse>("/settings/server-time"),
  projectStart: () => api.get<APIResponse>("/settings/project-start"),
  saveProjectStart: (start_date: string | null) =>
    api.post<APIResponse>("/settings/project-start", { start_date }),
  getLayout: () => api.get<APIResponse>("/settings/layout"),
  saveLayout: (payload: { pageOrder: string[]; hiddenPages: string[]; startPage: string; layouts?: any; activeLayout?: string }) =>
    api.post<APIResponse>("/settings/layout", payload),
};

// ── Health ────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get<APIResponse>("/health"),
};

export default api;

// ── Notes (Market / Portfolio notebooks) ─────────────────────
export const notesApi = {
  list:   (scope?: string) => api.get<APIResponse>("/notes" + (scope ? `?scope=${scope}` : "")),
  add:    (data: { scope: string; content: string; company_id?: number }) => api.post<APIResponse>("/notes", data),
  remove: (id: number) => api.delete<APIResponse>(`/notes/${id}`),
};

// ── Allocation / Rebalance ───────────────────────────────────
export const allocationApi = {
  get:        () => api.get<APIResponse>("/allocation"),
  setTargets: (items: { company_id: number; target_weight: number }[]) => api.put<APIResponse>("/allocation/targets", { items }),
  rebalance:  () => api.get<APIResponse>("/allocation/rebalance"),
  profitLiquidation: () => api.get<APIResponse>("/allocation/profit-liquidation"),
  setLiquidationThreshold: (threshold_pct: number) =>
    api.put<APIResponse>("/allocation/liquidation-threshold", { threshold_pct }),
  setCompanyThreshold: (company_id: number, threshold_pct: number | null) =>
    api.put<APIResponse>("/allocation/liquidation-threshold",
      threshold_pct == null ? { company_id, inherit: true } : { company_id, threshold_pct }),
};

// ── Backup ────────────────────────────────────────────────────
// ── Profile ───────────────────────────────────────────────────
export const profileApi = {
  get:    () => api.get<APIResponse>("/settings/profile"),
  save:   (name: string) => api.post<APIResponse>("/settings/profile", { name }),
  avatarUrl: (ver = 0) => `${BASE_URL}/settings/avatar?v=${ver}`,
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<APIResponse>("/settings/avatar", form, { timeout: 60000 });
  },
  removeAvatar: () => api.delete<APIResponse>("/settings/avatar"),
};

export const backupApi = {
  list:     () => api.get<APIResponse>("/backups"),
  // النسخة تُضمّن ملفات الكتب (قد تبلغ مئات الميجابايت) — مهلة طويلة بدل الـ30ث
  // الافتراضية، وإلا انقطع التنزيل/الرفع الكبير قبل اكتماله (كان سبب «لا يعمل»).
  download: () => api.get("/backups/download", { responseType: "blob", timeout: 600000 }),
  restore:  (file: File) => {
    const form = new FormData();
    form.append("file", file);
    // لا نضبط Content-Type يدوياً: ضبطه "multipart/form-data" بلا boundary
    // يمنع الخادم من تحليل الملف فتفشل الاستعادة. المتصفح يضبطه تلقائياً مع
    // الـboundary الصحيح عند تمرير FormData.
    return api.post<APIResponse>("/backups/restore", form, { timeout: 600000 });
  },
  factoryReset: () => api.post<APIResponse>("/backups/factory-reset", { confirm: "فورمات" }),
};

/* إدارة السيولة — خطّة الدفعات. القراءة تُعيد الحساب من الخادم (مصدر واحد)،
   والحفظ صريح لا تلقائي: الخطّة تُعدَّل عشرات المرّات في الجلسة. */
export const liquidityApi = {
  get:  () => api.get<APIResponse>("/liquidity"),
  save: (items: any[], tranche_value?: number) =>
    api.put<APIResponse>("/liquidity", { items, tranche_value }),
};
