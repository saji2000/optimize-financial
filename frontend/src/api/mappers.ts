import {
  PipelineRunRead,
  SignalRead,
  TranscriptDetailRead,
  TranscriptSummaryRead,
  TranscriptTurnRead,
  LLMUsageStepRead,
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
    cost: dto.usage.estimated_total_cost_usd,
    tokensIn: dto.usage.input_tokens,
    tokensOut: dto.usage.output_tokens,
    calls: dto.usage.calls,
    retries: dto.usage.retry_count,
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
    status: dto.review_status ?? "pending",
    flag: dto.flag ?? false,
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
  fallbackSteps: PipelineStep[] = [],
): PipelineStep[] {
  if (!run) return fallbackSteps;
  if (run.usage_by_step.length > 0) {
    return withDeterministicFinalFormattingStep(run.usage_by_step.map(mapUsageStep));
  }
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

function mapUsageStep(dto: LLMUsageStepRead, index: number): PipelineStep {
  const stepNumber = stepNumberFor(dto.pipeline_step, index);
  return {
    step: stepNumber,
    name: stepNameFor(dto.pipeline_step, dto.agent_name),
    status: "ok",
    model: dto.models.length > 0 ? dto.models.join(", ") : "No model recorded",
    prompt: dto.prompt_versions.length > 0 ? dto.prompt_versions.join(", ") : "No prompt recorded",
    retries: dto.retry_count,
    latency: "Not tracked",
    tokensIn: dto.input_tokens,
    tokensOut: dto.output_tokens,
    cost: dto.estimated_total_cost_usd,
  };
}

function stepNumberFor(pipelineStep: string, index: number) {
  const order: Record<string, number> = {
    transcript_preparation: 1,
    segment_signal_extraction: 2,
    consolidation_ranking: 3,
    evidence_validation: 4,
    final_formatting: 5,
  };
  return order[pipelineStep] || index + 1;
}

function stepNameFor(pipelineStep: string, agentName: string) {
  const names: Record<string, string> = {
    transcript_preparation: "Transcript preparation",
    segment_signal_extraction: "Segment signal extraction",
    consolidation_ranking: "Consolidation & ranking",
    evidence_validation: "Evidence validation",
    final_formatting: "Deterministic final formatting",
  };
  return names[pipelineStep] || agentName || pipelineStep;
}

function withDeterministicFinalFormattingStep(steps: PipelineStep[]): PipelineStep[] {
  if (steps.some((step) => step.step === 5)) {
    return steps.sort((a, b) => a.step - b.step);
  }
  const deterministicFinalStep: PipelineStep = {
    step: 5,
    name: "Deterministic final formatting",
    status: "ok",
    model: "No model recorded",
    prompt: "No prompt recorded",
    retries: 0,
    latency: "Not tracked",
    tokensIn: 0,
    tokensOut: 0,
    cost: 0,
  };
  return [
    ...steps,
    deterministicFinalStep,
  ].sort((a, b) => a.step - b.step);
}
