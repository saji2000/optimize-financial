import { apiGet } from "./client";
import type { PipelineRun } from "./generated-types";

export function getPipelineRuns() {
  return apiGet<PipelineRun[]>("/pipeline-runs");
}

