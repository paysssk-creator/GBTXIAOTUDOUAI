import DashboardLayout from "./components/layout/DashboardLayout";
import Overview from "./pages/Overview";
import AgentMonitor from "./pages/AgentMonitor";
import MarketData from "./pages/MarketData";
import AuditReport from "./pages/AuditReport";
import AIChat from "./pages/AIChat";
import NotFound from "./pages/NotFound";

export const routers = [
  {
    path: "/",
    element: <DashboardLayout />,
    children: [
      { index: true, element: <Overview /> },
      { path: "agents", element: <AgentMonitor /> },
      { path: "market", element: <MarketData /> },
      { path: "audit", element: <AuditReport /> },
      { path: "chat", element: <AIChat /> },
    ],
  },
  { path: "*", element: <NotFound /> },
];
