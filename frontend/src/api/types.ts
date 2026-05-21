import { EvidenceKind, SignalType, TranscriptStatus } from "../data/mockData";

export type DataMode = "mock" | "api" | "hybrid";

export interface TranscriptSummaryRead {
  id: string;
  title: string;
  status: string;
  created_at: string;
  driver_count: number;
  blocker_count: number;
}

export interface TranscriptRead {
  id: string;
  title: string;
  status: string;
}

export interface TranscriptTurnRead {
  id: string;
  transcript_id: string;
  sequence: number;
  timestamp: string | null;
  end_timestamp: string | null;
  speaker: string;
  speaker_role: string;
  text: string;
  source_chunk_id: string;
}

export interface SignalRead {
  id: string;
  transcript_id: string;
  item_type: SignalType;
  rank: number;
  category: string;
  advisor_quote: string;
  timestamp: string | null;
  evidence_strength: EvidenceKind;
  rationale: string;
}

export interface TranscriptDetailRead extends TranscriptSummaryRead {
  updated_at: string;
  error_type: string | null;
  error_message: string | null;
  turns: TranscriptTurnRead[];
  final_signals: SignalRead[];
}

export interface PipelineRunRead {
  id: string;
  transcript_id: string;
  status: TranscriptStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  error_type: string | null;
  error_message: string | null;
}
