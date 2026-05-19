export type TranscriptStatus = "queued" | "running" | "completed" | "failed";
export type SignalType = "driver" | "blocker";
export type EvidenceStrength = "explicit" | "implied";

export interface Transcript {
  id: string;
  title: string;
  status: TranscriptStatus;
}

export interface Signal {
  id: string;
  transcript_id: string;
  signal_type: SignalType;
  category: string;
  summary: string;
  evidence_quote: string;
  evidence_strength: EvidenceStrength;
  rationale: string;
}

export interface PipelineRun {
  id: string;
  transcript_id: string;
  status: TranscriptStatus;
}
