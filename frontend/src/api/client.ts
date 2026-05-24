import {
  AuthUserRead,
  BulkFeedbackResponse,
  DataMode,
  LoginResponse,
  PipelineRunRead,
  SignalFeedbackResponse,
  SignalRead,
  TranscriptDetailRead,
  TranscriptRead,
  TranscriptSummaryRead,
  TranscriptTurnRead,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:2030";
export const DATA_MODE: DataMode = parseDataMode(import.meta.env.VITE_DATA_MODE);
export const AUTH_SESSION_STORAGE_KEY = "optimize_auth_session";

export class ApiError extends Error {
  status: number;

  constructor(status: number, statusText: string) {
    super(`Request failed ${status} ${statusText}`);
    this.status = status;
  }
}

function parseDataMode(value: unknown): DataMode {
  return value === "mock" || value === "api" || value === "hybrid" ? value : "hybrid";
}

function endpoint(path: string) {
  return `${API_BASE}${path}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (!headers.has("authorization")) {
    const token = getStoredAccessToken();
    if (token) headers.set("authorization", `Bearer ${token}`);
  }

  const res = await fetch(endpoint(path), {
    ...init,
    headers,
  });
  if (!res.ok) {
    if (res.status === 401) window.dispatchEvent(new Event("optimize-auth-unauthorized"));
    throw new ApiError(res.status, res.statusText);
  }
  return res.json() as Promise<T>;
}

export function login(username: string, password: string) {
  return fetchJson<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(accessToken: string) {
  return fetchJson<AuthUserRead>("/auth/me", {
    headers: { authorization: `Bearer ${accessToken}` },
  });
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

export function updateSignalFeedback(
  signalId: string,
  patch: { review_status?: string; flag?: boolean; reviewer_notes?: string },
) {
  return fetchJson<SignalFeedbackResponse>(
    `/review/signals/${encodeURIComponent(signalId)}`,
    { method: "PATCH", body: JSON.stringify(patch) },
  );
}

export function bulkUpdateSignalFeedback(payload: {
  signal_ids: string[];
  review_status?: string;
  flag?: boolean;
  reviewer_notes?: string;
}) {
  return fetchJson<BulkFeedbackResponse>("/review/signals", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}


function getStoredAccessToken() {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { accessToken?: unknown };
    return typeof parsed.accessToken === "string" ? parsed.accessToken : null;
  } catch {
    return null;
  }
}
