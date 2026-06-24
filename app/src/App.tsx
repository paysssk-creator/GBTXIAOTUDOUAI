import { HashRouter } from "react-router-dom";
import { BackendProvider } from "./providers/BackendProvider";
import { CoreStateProvider } from "./providers/CoreStateProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import { BootCheckGate } from "./components/BootCheckGate";
import { BottomTabBar } from "./components/BottomTabBar";
import { AppUpdatePrompt } from "./components/AppUpdatePrompt";
import AppRoutes from "./AppRoutes";

function AppShell() {
  return (
    <div className="app-shell">
      <main className="app-main">
        <AppRoutes />
      </main>
      <BottomTabBar />
      <AppUpdatePrompt />
    </div>
  );
}

function App() {
  return (
    <HashRouter>
      <ThemeProvider>
        <BackendProvider>
          <CoreStateProvider>
            <BootCheckGate>
              <AppShell />
            </BootCheckGate>
          </CoreStateProvider>
        </BackendProvider>
      </ThemeProvider>
    </HashRouter>
  );
}

export default App;
