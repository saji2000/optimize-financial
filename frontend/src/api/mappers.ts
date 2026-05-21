import {
  PipelineRunRead,
  SignalRead,
  TranscriptDetailRead,
  TranscriptSummaryRead,
  TranscriptTurnRead,
} from "./types";
import {
  PipelineStep,
  Signal,
  Transcript,
  TranscriptStatus,
  TranscriptTurn,
} from "../data/mockData";
import { enrichmentFor } from "../data/demoEnrichment";

export function mapTranscriptSummary(dto: TranscriptSummaryRead): Transcript {
  const status = mapStatus(dto.status);
  const enrichment = enrichmentFor(dto.id, status);
  const signalCount = dto.driver_count + dto.blocker_count;
  return {
    id: dto.id,
    name: dto.title,
    uploaded: dateOnly(dto.created_at),
    processed: dateOnly(dto.created_at),
    status,
    drivers: dto.driver_count,
    blockers: dto.blocker_count,
    cost: enrichment.cost ?? 0,
    tokensIn: enrichment.tokensIn ?? 0,
    tokensOut: enrichment.tokensOut ?? 0,
    calls: enrichment.calls ?? 0,
    retries: enrichment.retries ?? 0,
    reviewState: enrichment.reviewState,
    exportReady: status === "completed" && signalCount > 0,
    duration: enrichment.duration,
    advisor: enrichment.advisor,
    client: enrichment.client,
  };
}

export function mapTranscriptDetail(dto: TranscriptDetailRead): Transcript {
  return {
    ...mapTranscriptSummary(dto),
    processed: dateOnly(dto.updated_at),
    exportReady: mapStatus(dto.status) === "completed" && dto.final_signals.length > 0,
  };
}

export function mapSignal(dto: SignalRead): Signal {
  return {
    id: dto.id,
    transcriptId: dto.transcript_id,
    type: dto.item_type,
    rank: dto.rank,
    category: dto.category,
    quote: dto.advisor_quote,
    timestamp: dto.timestamp || "00:00:00",
    evidence: dto.evidence_strength,
    rationale: dto.rationale,
    status: "pending",
  };
}

export function mapTurn(dto: TranscriptTurnRead): TranscriptTurn {
  const advisor = dto.speaker_role === "advisor";
  return {
    t: dto.timestamp || "00:00:00",
    who: advisor ? "Advisor" : "Client",
    name: advisor ? "Advisor" : repDisplayName(dto),
    text: dto.text,
  };
}

export function pipelineStepsForRun(
  run: PipelineRunRead | undefined,
  fallbackSteps: PipelineStep[],
): PipelineStep[] {
  if (!run) return fallbackSteps;
  const failed = run.status === "failed";
  return fallbackSteps.map((step) => ({
    ...step,
    status: failed && step.step === 3 ? "failed" : "ok",
  }));
}

export function mapStatus(value: string): TranscriptStatus {
  if (value === "completed" || value === "running" || value === "queued" || value === "failed") {
    return value;
  }
  return "queued";
}

function repDisplayName(dto: TranscriptTurnRead) {
  if (dto.speaker_role === "optimize_rep") return "Optimize rep";
  return dto.speaker || "Speaker";
}

function dateOnly(value: string) {
  return value.slice(0, 10);
}
