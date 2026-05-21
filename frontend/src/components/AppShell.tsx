import { Navigate, Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useAuth } from "../auth/AuthProvider";
import { DataProvider } from "../data/DataProvider";
import { SignalsProvider } from "../data/SignalsStore";

export function AppShell() {
  const { user, loading } = useAuth();
  if (loading) return <div className="auth-loading">Checking session...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <DataProvider>
      <SignalsProvider>
        <div className="shell">
          <Sidebar />
          <main className="main">
            <Outlet />
          </main>
        </div>
      </SignalsProvider>
    </DataProvider>
  );
}
