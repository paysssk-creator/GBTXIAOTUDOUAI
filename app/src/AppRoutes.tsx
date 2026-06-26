import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useBackend } from "./providers/BackendProvider";
import { useCoreState } from "./providers/CoreStateProvider";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import Skills from "./pages/Skills";
import Settings from "./pages/Settings";
import Welcome from "./pages/Welcome";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { initialized, apiKeySet } = useCoreState();
  const { safeMode } = useBackend();
  const location = useLocation();

  if (!initialized && !safeMode) {
    return (
      <div className="boot-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (safeMode && location.pathname === "/settings") {
    return <>{children}</>;
  }

  if (!apiKeySet && location.pathname !== "/welcome") {
    return <Navigate to="/welcome" replace />;
  }

  return <>{children}</>;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/welcome" element={<Welcome />} />
      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        }
      />
      <Route
        path="/skills"
        element={
          <ProtectedRoute>
            <Skills />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/home" replace />} />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
