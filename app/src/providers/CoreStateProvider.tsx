import { createContext, useContext, useEffect, useState } from "react";
import { fetchJSON } from "../lib/api";
import { useAppStore } from "../store";

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

  const refresh = async () => {
    try {
      const status = (await fetchJSON("/api/status")) as {
        api_key_set?: boolean;
        model?: string;
        version?: string;
      };
      setProfile({
        apiKeySet: !!status.api_key_set,
        model: status.model || "",
      });
    } catch {
      // backend might not be ready yet
    } finally {
      setInitialized(true);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const profile = useAppStore((state) => state.profile);

  return (
    <CoreStateContext.Provider
      value={{
        initialized,
        apiKeySet: profile.apiKeySet,
        model: profile.model,
        version: profile.model,
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
