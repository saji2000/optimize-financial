import { Outlet } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { DataProvider } from "./data/DataProvider";
import { SignalsProvider } from "./data/SignalsStore";

export function App() {
  return (
    <AuthProvider>
      <DataProvider>
        <SignalsProvider>
          <Outlet />
        </SignalsProvider>
      </DataProvider>
    </AuthProvider>
  );
}
