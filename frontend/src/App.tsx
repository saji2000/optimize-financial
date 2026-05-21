import { Outlet } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";

export function App() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}
