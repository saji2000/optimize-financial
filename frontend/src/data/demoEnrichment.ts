import { ReviewState, TranscriptStatus } from "./mockData";

export interface DemoEnrichment {
  advisor: string;
  client: string;
  duration: string;
  reviewState: ReviewState;
  cost?: number;
  tokensIn?: number;
  tokensOut?: number;
  calls?: number;
  retries?: number;
}

const seeded: Record<string, DemoEnrichment> = {
  "TR-2041": {
    advisor: "M. Okafor",
    client: "Hartman / Greer Family",
    duration: "47:12",
    reviewState: "pending",
    cost: 0.3812,
    tokensIn: 184230,
    tokensOut: 12410,
    calls: 14,
    retries: 1,
  },
  "TR-2040": {
    advisor: "S. Devarajan",
    client: "Liang Household",
    duration: "52:40",
    reviewState: "approved",
    cost: 0.4421,
    tokensIn: 211088,
    tokensOut: 14903,
    calls: 14,
    retries: 0,
  },
  "TR-2039": {
    advisor: "R. Toussaint",
    client: "Beauchamp Family Trust",
    duration: "38:55",
    reviewState: "pending",
    cost: 0.3104,
    tokensIn: 152711,
    tokensOut: 10118,
    calls: 14,
    retries: 2,
  },
};

const advisors = ["Advisor TBD", "M. Okafor", "S. Devarajan", "R. Toussaint", "C. Yamamoto"];
const firms = ["Prospective firm", "Northshore Wealth", "Cedar Ridge Advisory", "Meridian Planning"];

export function enrichmentFor(transcriptId: string, status: TranscriptStatus): DemoEnrichment {
  const known = seeded[transcriptId];
  if (known) return known;
  const n = stableNumber(transcriptId);
  const completed = status === "completed";
  return {
    advisor: completed ? advisors[n % advisors.length] : "Advisor TBD",
    client: completed ? firms[n % firms.length] : "Prospective firm",
    duration: completed ? `${36 + (n % 23)}:${String(10 + (n % 49)).padStart(2, "0")}` : "-",
    reviewState: completed ? "pending" : "—",
    cost: completed ? Number((0.24 + (n % 37) / 1000).toFixed(4)) : 0,
    tokensIn: completed ? 120000 + n * 317 : 0,
    tokensOut: completed ? 7200 + n * 41 : 0,
    calls: completed ? 14 : status === "running" ? 8 : 0,
    retries: n % 3,
  };
}

function stableNumber(value: string) {
  let n = 0;
  for (const ch of value) n = (n * 31 + ch.charCodeAt(0)) % 997;
  return n;
}
