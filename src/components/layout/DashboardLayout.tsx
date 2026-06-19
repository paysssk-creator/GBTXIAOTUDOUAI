import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function DashboardLayout() {
  return (
    <div className="flex h-full bg-background">
      <Sidebar />
      <main className="flex-1 ml-60 flex flex-col min-h-full overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
