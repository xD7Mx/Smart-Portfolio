import { create } from "zustand";

const TOKEN_KEY = "sp_token";

interface AuthState {
  isOwner: boolean;
  login: (token: string) => void;
  logout: () => void;
}

/** Reactive owner-session state — the site is public read-only, this is
 * the single source of truth the whole UI uses to decide whether to show
 * write controls (add/edit/delete buttons, forms) at all, not just rely
 * on the backend silently rejecting them. */
export const useAuthStore = create<AuthState>((set) => ({
  isOwner: !!localStorage.getItem(TOKEN_KEY),
  login: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    set({ isOwner: true });
  },
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ isOwner: false });
  },
}));

export const getToken = () => localStorage.getItem(TOKEN_KEY);
