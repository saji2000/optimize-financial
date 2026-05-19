import { apiGet } from "./client";
import type { Signal } from "./generated-types";

export function getSignals() {
  return apiGet<Signal[]>("/signals");
}

