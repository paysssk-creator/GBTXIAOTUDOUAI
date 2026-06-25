import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { fetchData } from "../lib/api";
import { useAppStore } from "../store";
import { useBackend } from "./BackendProvider";

interface CoreState {
  initialized: boolean;
  apiKeySet: boolean;
  model: string;
  version: string;
  refresh: () => Promise<void>;
}

const CoreStateContext = createContext<CoreState | null>(null);

export function CoreStateProvider({ children }: { children: React.ReactNode }) {
  const [initialized, setInitialized] = useState(false);
  const setProfile = useAppStore((state) => state.setProfile);
  const { status } = useBackend();

  const refresh = useCallback(async () => {
    try {
      const status = await fetchData<{
        api_key_set?: boolean;
        model?: string;
        version?: string;
      }>("/api/status");
      setProfile({
        apiKeySet: !!status.api_key_set,
        model: status.model || "",
        version: status.version || "",
      });
    } catch {
      // backend might not be ready yet
    } finally {
      setInitialized(true);
    }
  }, [setProfile]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Re-fetch profile once backend becomes healthy.
  useEffect(() => {
    if (status === "healthy") {
      refresh();
    }
  }, [status, refresh]);

  const profile = useAppStore((state) => state.profile);

  return (
    <CoreStateContext.Provider
      value={{
        initialized,
        apiKeySet: profile.apiKeySet,
        model: profile.model,
        version: profile.version,
        refresh,
      }}>
      {children}
    </CoreStateContext.Provider>
  );
}

export function useCoreState() {
  const ctx = useContext(CoreStateContext);
  if (!ctx) throw new Error("useCoreState must be used within CoreStateProvider");
  return ctx;
}
