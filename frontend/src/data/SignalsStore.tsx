import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { Signal } from "./mockData";
import { useData } from "./DataProvider";
import { updateSignalFeedback } from "../api/client";
import { DATA_MODE } from "../api/client";

interface SignalsContextValue {
  signals: Signal[];
  setSignals: React.Dispatch<React.SetStateAction<Signal[]>>;
  updateSignal: (id: string, patch: Partial<Signal>) => void;
  signalsForTranscript: (transcriptId: string | undefined) => Signal[];
}

const SignalsContext = createContext<SignalsContextValue | undefined>(undefined);

export function SignalsProvider({ children }: { children: ReactNode }) {
  const { apiSignals } = useData();
  const [localState, setLocalState] = useState<Record<string, Pick<Signal, "status" | "flag">>>({});
  const [signals, setSignals] = useState<Signal[]>(() => mergeLocal(apiSignals, localState));

  useEffect(() => {
    setSignals(mergeLocal(apiSignals, localState));
  }, [apiSignals, localState]);

  function updateSignal(id: string, patch: Partial<Signal>) {
    if ("status" in patch || "flag" in patch) {
      setLocalState((current) => {
        const existing = current[id] || {};
        return {
          ...current,
          [id]: {
            status: patch.status ?? existing.status ?? "pending",
            flag: patch.flag ?? existing.flag,
          },
        };
      });

      if (DATA_MODE !== "mock") {
        const apiPatch: Record<string, unknown> = {};
        if ("status" in patch && patch.status !== undefined) {
          apiPatch.review_status = patch.status;
        }
        if ("flag" in patch && patch.flag !== undefined) {
          apiPatch.flag = patch.flag;
        }
        updateSignalFeedback(id, apiPatch).catch((err) => {
          console.error("Failed to persist signal feedback:", err);
        });
      }
    }
    setSignals((arr) => arr.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }
  function signalsForTranscript(transcriptId: string | undefined) {
    return signals.filter((s) => !transcriptId || s.transcriptId === transcriptId);
  }
  return (
    <SignalsContext.Provider value={{ signals, setSignals, updateSignal, signalsForTranscript }}>
      {children}
    </SignalsContext.Provider>
  );
}

export function useSignals() {
  const ctx = useContext(SignalsContext);
  if (!ctx) throw new Error("useSignals must be used within SignalsProvider");
  return ctx;
}

function mergeLocal(signals: Signal[], localState: Record<string, Pick<Signal, "status" | "flag">>) {
  return signals.map((signal) => ({
    ...signal,
    ...localState[signal.id],
  }));
}
