import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ApiError,
  DATA_MODE,
  getTranscript,
  listPipelineRuns,
  listSignals,
  listTranscriptTurns,
  listTranscripts,
} from "../api/client";
import { mapSignal, mapTranscriptDetail, mapTranscriptSummary, mapTurn, pipelineStepsForRun } from "../api/mappers";
import { PipelineRunRead } from "../api/types";
import {
  activity as mockActivity,
  pipelineSteps as mockPipelineSteps,
  signals as mockSignals,
  transcripts as mockTranscripts,
  transcriptTurns as mockTranscriptTurns,
  ActivityEntry,
  PipelineStep,
  Signal,
  Transcript,
  TranscriptTurn,
} from "./mockData";

interface DataContextValue {
  mode: typeof DATA_MODE;
  source: "mock" | "api";
  loading: boolean;
  error: string | null;
  transcripts: Transcript[];
  apiSignals: Signal[];
  pipelineRuns: PipelineRunRead[];
  activity: ActivityEntry[];
  refresh: () => Promise<void>;
  stepsForTranscript: (transcriptId: string | undefined) => PipelineStep[];
}

interface TranscriptDetailState {
  transcript: Transcript | undefined;
  turns: TranscriptTurn[];
  loading: boolean;
  error: string | null;
}

const DataContext = createContext<DataContextValue | undefined>(undefined);

export function DataProvider({ children }: { children: ReactNode }) {
  const [source, setSource] = useState<"mock" | "api">(DATA_MODE === "api" ? "api" : "mock");
  const [loading, setLoading] = useState(DATA_MODE !== "mock");
  const [error, setError] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[]>(() =>
    DATA_MODE === "api" ? [] : cloneTranscripts(mockTranscripts),
  );
  const [apiSignals, setApiSignals] = useState<Signal[]>(() =>
    DATA_MODE === "api" ? [] : cloneSignals(mockSignals),
  );
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRunRead[]>([]);

  const refresh = useCallback(async () => {
    if (DATA_MODE === "mock") {
      setSource("mock");
      setTranscripts(cloneTranscripts(mockTranscripts));
      setApiSignals(cloneSignals(mockSignals));
      setPipelineRuns([]);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [transcriptRows, signalRows, runRows] = await Promise.all([
        listTranscripts(),
        listSignals(),
        listPipelineRuns(),
      ]);
      setSource("api");
      setTranscripts(transcriptRows.map(mapTranscriptSummary));
      setApiSignals(signalRows.map(mapSignal));
      setPipelineRuns(runRows);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load backend data";
      setError(message);
      if (err instanceof ApiError && err.status === 401) {
        setSource("api");
        setTranscripts([]);
        setApiSignals([]);
        setPipelineRuns([]);
      } else if (DATA_MODE === "hybrid") {
        setSource("mock");
        setTranscripts(cloneTranscripts(mockTranscripts));
        setApiSignals(cloneSignals(mockSignals));
        setPipelineRuns([]);
      } else {
        setTranscripts([]);
        setApiSignals([]);
        setPipelineRuns([]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const activity = useMemo(() => {
    if (source === "mock") return mockActivity;
    return transcripts.slice(0, 6).map((t): ActivityEntry => ({
      id: t.id,
      who: t.status === "completed" ? t.advisor : "system",
      when: t.processed || t.uploaded,
      action: statusAction(t.status),
      n: t.drivers + t.blockers,
    }));
  }, [source, transcripts]);

  const stepsForTranscript = useCallback(
    (transcriptId: string | undefined) => {
      if (source === "mock") return pipelineStepsForRun(undefined, mockPipelineSteps);
      const run = [...pipelineRuns]
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .find((item) => item.transcript_id === transcriptId);
      return pipelineStepsForRun(run);
    },
    [pipelineRuns, source],
  );

  return (
    <DataContext.Provider
      value={{
        mode: DATA_MODE,
        source,
        loading,
        error,
        transcripts,
        apiSignals,
        pipelineRuns,
        activity,
        refresh,
        stepsForTranscript,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error("useData must be used within DataProvider");
  return ctx;
}

export function useTranscripts() {
  return useData().transcripts;
}

export function usePipelineSteps(transcriptId: string | undefined) {
  return useData().stepsForTranscript(transcriptId);
}

export function useActivity() {
  return useData().activity;
}

export function useTranscriptDetail(transcriptId: string | undefined): TranscriptDetailState {
  const { source, transcripts } = useData();
  const summary = transcripts.find((x) => x.id === transcriptId) || transcripts[0];
  const [state, setState] = useState<TranscriptDetailState>({
    transcript: source === "mock" ? summary : undefined,
    turns: source === "mock" ? mockTranscriptTurns : [],
    loading: source !== "mock",
    error: null,
  });

  useEffect(() => {
    if (!transcriptId) {
      setState({ transcript: summary, turns: source === "mock" ? mockTranscriptTurns : [], loading: false, error: null });
      return;
    }
    if (source === "mock") {
      setState({ transcript: summary, turns: mockTranscriptTurns, loading: false, error: null });
      return;
    }

    let alive = true;
    setState((current) => ({ ...current, transcript: summary, loading: true, error: null }));
    Promise.all([getTranscript(transcriptId), listTranscriptTurns(transcriptId)])
      .then(([detail, turns]) => {
        if (!alive) return;
        setState({
          transcript: mapTranscriptDetail(detail),
          turns: turns.map(mapTurn),
          loading: false,
          error: null,
        });
      })
      .catch((err) => {
        if (!alive) return;
        const message = err instanceof Error ? err.message : "Unable to load transcript detail";
        setState({
          transcript: summary,
          turns: DATA_MODE === "hybrid" ? mockTranscriptTurns : [],
          loading: false,
          error: message,
        });
      });
    return () => {
      alive = false;
    };
  }, [source, summary, transcriptId]);

  return state;
}

function cloneTranscripts(rows: Transcript[]) {
  return rows.map((row) => ({ ...row }));
}

function cloneSignals(rows: Signal[]) {
  return rows.map((row) => ({ ...row }));
}

function statusAction(status: Transcript["status"]) {
  if (status === "completed") return "completed processing";
  if (status === "running") return "started processing";
  if (status === "failed") return "failed during processing";
  return "queued for processing";
}
