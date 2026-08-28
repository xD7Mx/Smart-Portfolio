import { create } from "zustand";

/** المحفظة النشطة — يُرسَل معرّفها في ترويسة X-Portfolio-Id مع كل طلب، فتُعزَل
 * بيانات كل محفظة على حدة. ووضع «توحيد الثروة» (aggregate) يُرسَل في ترويسة
 * X-Portfolio-Aggregate فتُجمَع القراءة عبر كل المحافظ. كلاهما يُخزَّن محليًا. */
const KEY = "sp_active_portfolio";
const AGG_KEY = "sp_wealth_unified";

export const getActivePortfolioId = (): string | null => localStorage.getItem(KEY);
export const getWealthUnified = (): boolean => localStorage.getItem(AGG_KEY) === "1";

interface PortfolioState {
  activeId: string | null;
  unified: boolean;
  setActive: (id: number | string | null) => void;
  setUnified: (on: boolean) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  activeId: localStorage.getItem(KEY),
  unified: localStorage.getItem(AGG_KEY) === "1",
  setActive: (id) => {
    if (id === null || id === undefined || id === "") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, String(id));
    set({ activeId: id != null && id !== "" ? String(id) : null });
  },
  setUnified: (on) => {
    if (on) localStorage.setItem(AGG_KEY, "1");
    else localStorage.removeItem(AGG_KEY);
    set({ unified: on });
  },
}));
