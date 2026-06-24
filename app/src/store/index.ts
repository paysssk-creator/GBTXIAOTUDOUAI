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
  freeTier: boolean;
}

interface AppState {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;

  backend: BackendInfo;
  setBackendStatus: (status: BackendInfo["status"]) => void;
  setBackendInfo: (info: Partial<BackendInfo>) => void;
  appendBackendLog: (line: string) => void;

  profile: UserProfile;
  setProfile: (profile: Partial<UserProfile>) => void;
}

const MAX_LOG_LINES = 200;

export const useAppStore = create<AppState>((set) => ({
  theme: "dark",
  setTheme: (theme) => {
    set({ theme });
    applyTheme(theme);
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
    freeTier: true,
  },
  setProfile: (profile) =>
    set((state) => ({ profile: { ...state.profile, ...profile } })),
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
