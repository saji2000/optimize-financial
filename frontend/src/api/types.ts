import { EvidenceKind, SignalType, TranscriptStatus } from "../data/mockData";

export type DataMode = "mock" | "api" | "hybrid";

export interface AuthUserRead {
  username: string;
  name: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUserRead;
}

export interface TranscriptSummaryRead {
  id: string;
  title: string;
  status: string;
  created_at: string;
  driver_count: number;
  blocker_count: number;
  usage: LLMUsageSummaryRead;
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
  review_status: "pending" | "approved" | "rejected";
  flag: boolean;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
}

export interface SignalFeedbackResponse {
  signal_id: string;
  review_status: "pending" | "approved" | "rejected";
  flag: boolean;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
}

export interface BulkFeedbackResponse {
  updated: SignalFeedbackResponse[];
  not_found: string[];
}

export interface TranscriptDetailRead extends TranscriptSummaryRead {
  updated_at: string;
  error_type: string | null;
  error_message: string | null;
  turns: TranscriptTurnRead[];
  final_signals: SignalRead[];
}

export interface LLMUsageSummaryRead {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_total_cost_usd: number;
  retry_count: number;
  latest_pricing_version: string | null;
}

export interface LLMUsageStepRead {
  pipeline_step: string;
  agent_name: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_total_cost_usd: number;
  retry_count: number;
  models: string[];
  prompt_versions: string[];
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
  usage: LLMUsageSummaryRead;
  usage_by_step: LLMUsageStepRead[];
}
