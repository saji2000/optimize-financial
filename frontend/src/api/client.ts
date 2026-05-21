import {
  DataMode,
  PipelineRunRead,
  SignalRead,
  TranscriptDetailRead,
  TranscriptRead,
  TranscriptSummaryRead,
  TranscriptTurnRead,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const DATA_MODE: DataMode = parseDataMode(import.meta.env.VITE_DATA_MODE);

function parseDataMode(value: unknown): DataMode {
  return value === "mock" || value === "api" || value === "hybrid" ? value : "hybrid";
}

function endpoint(path: string) {
  return `${API_BASE}${path}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(endpoint(path), {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : {
      "content-type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`Request failed ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function listTranscripts() {
  return fetchJson<TranscriptSummaryRead[]>("/transcripts");
}

export function getTranscript(id: string) {
  return fetchJson<TranscriptDetailRead>(`/transcripts/${encodeURIComponent(id)}`);
}

export function listTranscriptTurns(id: string) {
  return fetchJson<TranscriptTurnRead[]>(`/transcripts/${encodeURIComponent(id)}/turns`);
}

export function listSignals(transcriptId?: string) {
  const query = transcriptId ? `?transcript_id=${encodeURIComponent(transcriptId)}` : "";
  return fetchJson<SignalRead[]>(`/signals${query}`);
}

export function listPipelineRuns() {
  return fetchJson<PipelineRunRead[]>("/pipeline-runs");
}

export function uploadTranscript(file: File) {
  const data = new FormData();
  data.append("file", file);
  data.append("title", file.name.replace(/\.txt$/i, ""));
  return fetchJson<TranscriptRead>("/transcripts", {
    method: "POST",
    body: data,
  });
}
