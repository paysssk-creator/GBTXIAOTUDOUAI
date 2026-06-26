import { useEffect } from "react";
import { HashRouter } from "react-router-dom";
import { BackendProvider } from "./providers/BackendProvider";
import { CoreStateProvider } from "./providers/CoreStateProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import { ToastProvider } from "./providers/ToastProvider";
import { BootCheckGate } from "./components/BootCheckGate";
import { BottomTabBar } from "./components/BottomTabBar";
import { AppUpdatePrompt } from "./components/AppUpdatePrompt";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { KeyboardShortcutsHelp } from "./components/KeyboardShortcutsHelp";
import { useAppStore } from "./store";
import AppRoutes from "./AppRoutes";

function AppShell() {
  const toggleTheme = useAppStore((state) => state.toggleTheme);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "t") {
        e.preventDefault();
        toggleTheme();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleTheme]);

  return (
    <div className="app-shell">
      <main className="app-main">
        <ErrorBoundary>
          <AppRoutes />
        </ErrorBoundary>
      </main>
      <BottomTabBar />
      <AppUpdatePrompt />
      <KeyboardShortcutsHelp />
    </div>
  );
}

function App() {
  return (
    <HashRouter>
      <ThemeProvider>
        <ToastProvider>
          <BackendProvider>
            <CoreStateProvider>
              <BootCheckGate>
                <AppShell />
              </BootCheckGate>
            </CoreStateProvider>
          </BackendProvider>
        </ToastProvider>
      </ThemeProvider>
    </HashRouter>
  );
}

export default App;
