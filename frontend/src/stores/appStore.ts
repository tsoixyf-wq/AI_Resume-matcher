"use client";

import { create } from "zustand";

export type ThemeMode = "light" | "dark";

interface AppState {
  theme: ThemeMode;
  sidebarCollapsed: boolean;
  toggleTheme: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

const getInitialTheme = (): ThemeMode => {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("app-theme");
    if (stored === "dark" || stored === "light") return stored;
  }
  return "light";
};

export const useAppStore = create<AppState>((set) => ({
  theme: "light", // Default before hydration
  sidebarCollapsed: false,
  toggleTheme: () =>
    set((s) => {
      const next: ThemeMode = s.theme === "light" ? "dark" : "light";
      localStorage.setItem("app-theme", next);
      return { theme: next };
    }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}));

// Hydrate theme from localStorage on client side
if (typeof window !== "undefined") {
  useAppStore.setState({ theme: getInitialTheme() });
}
