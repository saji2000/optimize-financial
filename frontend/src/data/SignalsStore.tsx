import { createContext, useContext, useState, ReactNode } from "react";
import { signals as initialSignals, Signal } from "./mockData";

interface SignalsContextValue {
  signals: Signal[];
  setSignals: React.Dispatch<React.SetStateAction<Signal[]>>;
  updateSignal: (id: string, patch: Partial<Signal>) => void;
}

const SignalsContext = createContext<SignalsContextValue | undefined>(undefined);

export function SignalsProvider({ children }: { children: ReactNode }) {
  const [signals, setSignals] = useState<Signal[]>(() => initialSignals.map((s) => ({ ...s })));
  function updateSignal(id: string, patch: Partial<Signal>) {
    setSignals((arr) => arr.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }
  return (
    <SignalsContext.Provider value={{ signals, setSignals, updateSignal }}>
      {children}
    </SignalsContext.Provider>
  );
}

export function useSignals() {
  const ctx = useContext(SignalsContext);
  if (!ctx) throw new Error("useSignals must be used within SignalsProvider");
  return ctx;
}
