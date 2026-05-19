import { apiGet } from "./client";
import type { Transcript } from "./generated-types";

export function getTranscripts() {
  return apiGet<Transcript[]>("/transcripts");
}

