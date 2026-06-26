import { create } from "zustand";

export type ThemeMode = "system" | "light" | "dark";

export interface BackendInfo {
  status: "idle" | "starting" | "healthy" | "failed";
  port: number;
  dataDir: string;
  logs: string[];
}

export interface UserProfile {
  apiKeySet: boolean;
  model: string;
  version: string;
  freeTier: boolean;
}

const THEME_CYCLE: ThemeMode[] = ["dark", "light", "system"];

interface AppState {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;

  backend: BackendInfo;
  setBackendStatus: (status: BackendInfo["status"]) => void;
  setBackendInfo: (info: Partial<BackendInfo>) => void;
  appendBackendLog: (line: string) => void;

  profile: UserProfile;
  setProfile: (profile: Partial<UserProfile>) => void;

  lastProvider: string;
  setLastProvider: (provider: string) => void;
}

const MAX_LOG_LINES = 200;

function loadTheme(): ThemeMode {
  try {
    const saved = localStorage.getItem("gbt-theme");
    if (saved === "light" || saved === "dark" || saved === "system") return saved;
  } catch {
    // ignore
  }
  return "dark";
}

function saveTheme(theme: ThemeMode) {
  try {
    localStorage.setItem("gbt-theme", theme);
  } catch {
    // ignore
  }
}

function loadLastProvider(): string {
  try {
    const saved = localStorage.getItem("gbt-last-provider");
    if (saved) return saved;
  } catch {
    // ignore
  }
  return "OPENAI_API_KEY";
}

function saveLastProvider(provider: string) {
  try {
    localStorage.setItem("gbt-last-provider", provider);
  } catch {
    // ignore
  }
}

export const useAppStore = create<AppState>((set) => ({
  theme: loadTheme(),
  setTheme: (theme) => {
    set({ theme });
    saveTheme(theme);
    applyTheme(theme);
  },
  toggleTheme: () => {
    set((state) => {
      const nextIndex = (THEME_CYCLE.indexOf(state.theme) + 1) % THEME_CYCLE.length;
      const next = THEME_CYCLE[nextIndex];
      saveTheme(next);
      applyTheme(next);
      return { theme: next };
    });
  },

  backend: {
    status: "idle",
    port: 8765,
    dataDir: "",
    logs: [],
  },
  setBackendStatus: (status) => set((state) => ({ backend: { ...state.backend, status } })),
  setBackendInfo: (info) =>
    set((state) => ({ backend: { ...state.backend, ...info } })),
  appendBackendLog: (line) =>
    set((state) => {
      const logs = [...state.backend.logs, line];
      if (logs.length > MAX_LOG_LINES) logs.splice(0, logs.length - MAX_LOG_LINES);
      return { backend: { ...state.backend, logs } };
    }),

  profile: {
    apiKeySet: false,
    model: "",
    version: "",
    freeTier: true,
  },
  setProfile: (profile) =>
    set((state) => ({ profile: { ...state.profile, ...profile } })),

  lastProvider: loadLastProvider(),
  setLastProvider: (provider) => {
    set({ lastProvider: provider });
    saveLastProvider(provider);
  },
}));

function applyTheme(theme: ThemeMode) {
  const root = document.documentElement;
  if (theme === "system") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", prefersDark ? "dark" : "light");
  } else {
    root.setAttribute("data-theme", theme);
  }
}

// Sync theme on initial load
applyTheme(useAppStore.getState().theme);
