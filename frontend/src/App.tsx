import { Outlet } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { SignalsProvider } from "./data/SignalsStore";

export function App() {
  return (
    <AuthProvider>
      <SignalsProvider>
        <Outlet />
      </SignalsProvider>
    </AuthProvider>
  );
}
