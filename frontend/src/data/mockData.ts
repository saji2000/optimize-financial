export type TranscriptStatus = "completed" | "running" | "queued" | "failed";
export type ReviewState = "pending" | "approved" | "rejected" | "—";

export interface Transcript {
  id: string;
  name: string;
  uploaded: string;
  processed: string;
  status: TranscriptStatus;
  drivers: number;
  blockers: number;
  cost: number;
  tokensIn: number;
  tokensOut: number;
  calls: number;
  retries: number;
  reviewState: ReviewState;
  exportReady: boolean;
  duration: string;
  advisor: string;
  client: string;
}

export interface TranscriptTurn {
  t: string;
  who: "Advisor" | "Client";
  name: string;
  text: string;
}

export type SignalType = "driver" | "blocker";
export type EvidenceKind = "explicit" | "implied";
export type SignalStatus = "pending" | "approved" | "rejected";

export interface Signal {
  id: string;
  transcriptId: string;
  type: SignalType;
  rank: number;
  category: string;
  quote: string;
  timestamp: string;
  evidence: EvidenceKind;
  rationale: string;
  status: SignalStatus;
  flag?: boolean;
}

export interface PipelineStep {
  step: number;
  name: string;
  status: "ok" | "failed";
  model: string;
  prompt: string;
  retries: number;
  latency: string;
  tokensIn: number;
  tokensOut: number;
  cost: number;
}

export interface ActivityEntry {
  id: string;
  who: string;
  when: string;
  action: string;
  n: number;
}

export const CATEGORIES_DRIVER = [
  "Fee Transparency",
  "Tax Efficiency",
  "Performance vs Benchmark",
  "Advisor Trust",
  "Risk Alignment",
  "Estate Planning",
  "Cash Flow Clarity",
  "Onboarding Experience",
  "Reporting Quality",
];

export const CATEGORIES_BLOCKER = [
  "Hidden Fees",
  "Tax Drag",
  "Underperformance",
  "Communication Gap",
  "Risk Mismatch",
  "Account Friction",
  "Service Lapses",
  "Statement Confusion",
];

export const transcripts: Transcript[] = [
  {
    id: "TR-2041",
    name: "Hartman-Greer · Q2 Review",
    uploaded: "2026-05-12",
    processed: "2026-05-12",
    status: "completed",
    drivers: 5,
    blockers: 3,
    cost: 0.3812,
    tokensIn: 184230,
    tokensOut: 12410,
    calls: 14,
    retries: 1,
    reviewState: "pending",
    exportReady: true,
    duration: "47:12",
    advisor: "M. Okafor",
    client: "Hartman / Greer Family",
  },
  {
    id: "TR-2040",
    name: "Liang Household · Annual",
    uploaded: "2026-05-11",
    processed: "2026-05-11",
    status: "completed",
    drivers: 6,
    blockers: 2,
    cost: 0.4421,
    tokensIn: 211088,
    tokensOut: 14903,
    calls: 14,
    retries: 0,
    reviewState: "approved",
    exportReady: true,
    duration: "52:40",
    advisor: "S. Devarajan",
    client: "Liang Household",
  },
  {
    id: "TR-2039",
    name: "Beauchamp Trust · Onboarding",
    uploaded: "2026-05-10",
    processed: "2026-05-10",
    status: "completed",
    drivers: 4,
    blockers: 4,
    cost: 0.3104,
    tokensIn: 152711,
    tokensOut: 10118,
    calls: 14,
    retries: 2,
    reviewState: "pending",
    exportReady: true,
    duration: "38:55",
    advisor: "R. Toussaint",
    client: "Beauchamp Family Trust",
  },
  {
    id: "TR-2038",
    name: "Okonkwo & Sons · Q2",
    uploaded: "2026-05-09",
    processed: "2026-05-09",
    status: "running",
    drivers: 0,
    blockers: 0,
    cost: 0.2210,
    tokensIn: 121400,
    tokensOut: 6021,
    calls: 9,
    retries: 0,
    reviewState: "—",
    exportReady: false,
    duration: "41:02",
    advisor: "C. Yamamoto",
    client: "Okonkwo & Sons Holdings",
  },
  {
    id: "TR-2037",
    name: "Pereira Retirement Plan",
    uploaded: "2026-05-08",
    processed: "2026-05-08",
    status: "completed",
    drivers: 7,
    blockers: 1,
    cost: 0.5102,
    tokensIn: 242031,
    tokensOut: 18204,
    calls: 14,
    retries: 0,
    reviewState: "approved",
    exportReady: true,
    duration: "58:11",
    advisor: "M. Okafor",
    client: "Pereira Retirement",
  },
  {
    id: "TR-2036",
    name: "Klein Foundation · Strategy",
    uploaded: "2026-05-08",
    processed: "2026-05-08",
    status: "failed",
    drivers: 0,
    blockers: 0,
    cost: 0.1422,
    tokensIn: 88210,
    tokensOut: 0,
    calls: 6,
    retries: 3,
    reviewState: "—",
    exportReady: false,
    duration: "—",
    advisor: "S. Devarajan",
    client: "Klein Foundation",
  },
  {
    id: "TR-2035",
    name: "Vanderberg · Wealth Transfer",
    uploaded: "2026-05-07",
    processed: "2026-05-07",
    status: "completed",
    drivers: 5,
    blockers: 2,
    cost: 0.3940,
    tokensIn: 198440,
    tokensOut: 13201,
    calls: 14,
    retries: 1,
    reviewState: "rejected",
    exportReady: false,
    duration: "44:21",
    advisor: "R. Toussaint",
    client: "Vanderberg Family Office",
  },
  {
    id: "TR-2034",
    name: "Aoki–Bell · Discovery",
    uploaded: "2026-05-06",
    processed: "2026-05-06",
    status: "queued",
    drivers: 0,
    blockers: 0,
    cost: 0,
    tokensIn: 0,
    tokensOut: 0,
    calls: 0,
    retries: 0,
    reviewState: "—",
    exportReady: false,
    duration: "—",
    advisor: "C. Yamamoto",
    client: "Aoki–Bell Partnership",
  },
  {
    id: "TR-2033",
    name: "Marston Estate · Q2",
    uploaded: "2026-05-05",
    processed: "2026-05-05",
    status: "completed",
    drivers: 4,
    blockers: 3,
    cost: 0.3621,
    tokensIn: 174221,
    tokensOut: 11820,
    calls: 14,
    retries: 0,
    reviewState: "approved",
    exportReady: true,
    duration: "46:18",
    advisor: "M. Okafor",
    client: "Marston Estate",
  },
];

export const transcriptTurns: TranscriptTurn[] = [
  { t: "00:00:12", who: "Advisor", name: "M. Okafor", text: "Thanks for coming in today. Before we get into the rebalance, I want to flag — your statements last quarter had two trailing fees that weren't itemized cleanly. We caught it, and you'll see them broken out from now on." },
  { t: "00:01:48", who: "Client", name: "L. Hartman", text: "Honestly, that's been the thing I've been most uneasy about. Every time I see the statement I'm not sure what I'm actually paying versus what's bundled." },
  { t: "00:02:30", who: "Advisor", name: "M. Okafor", text: "Understood. We've moved you to the unbundled fee schedule. It's a touch higher headline number but everything's visible." },
  { t: "00:03:55", who: "Client", name: "K. Greer", text: "And on the tax piece — last year we got hit harder than we expected on the non-registered side. Can we make sure we're not crystallizing gains we don't have to?" },
  { t: "00:05:02", who: "Advisor", name: "M. Okafor", text: "Yes — we're going to do the rebalance in stages, harvest the GIC roll-off losses first, and keep the deferred names in the corporate account where the rate is lower." },
  { t: "00:07:18", who: "Client", name: "L. Hartman", text: "Good. Last thing — when Karen's mother passed, dealing with the estate side of your firm was rough. Two months to get a statement reissued. If something happens to me I don't want her going through that." },
  { t: "00:08:44", who: "Advisor", name: "M. Okafor", text: "That's fair, and that was a service failure. I've personally introduced you to Renée on the estate desk, and we've pre-built the beneficiary file so reissues are 48 hours, not weeks." },
  { t: "00:11:02", who: "Client", name: "K. Greer", text: "I appreciate that. The personal introduction matters. The previous firm — it always felt like we were just an account number." },
  { t: "00:13:30", who: "Advisor", name: "M. Okafor", text: "On performance — we're 180 bps ahead of the blended benchmark trailing twelve. I want to be honest that a chunk of that is the energy overweight, which we'll trim next quarter." },
  { t: "00:15:55", who: "Client", name: "L. Hartman", text: "I trust the call. The transparency on where the return came from is — that's the difference from where we were before." },
  { t: "00:18:12", who: "Advisor", name: "M. Okafor", text: "On the reporting side — the new quarterly PDF will include the after-tax return number you asked for. That should make the family meetings with the kids easier." },
  { t: "00:20:01", who: "Client", name: "K. Greer", text: "Good. The old reports — we literally couldn't explain them to our son. He's the one who'd take this over eventually." },
  { t: "00:24:45", who: "Advisor", name: "M. Okafor", text: "Last item — the cash management piece. The high-interest account is now yielding 4.1%. Your idle cash was earning 0.05% at the bank." },
  { t: "00:26:08", who: "Client", name: "L. Hartman", text: "That alone — that single change — is meaningful. We had no idea." },
];

export const signals: Signal[] = [
  {
    id: "S-001", transcriptId: "TR-2041", type: "driver", rank: 1,
    category: "Fee Transparency",
    quote: "Every time I see the statement I'm not sure what I'm actually paying versus what's bundled.",
    timestamp: "00:01:48",
    evidence: "explicit",
    rationale: "Client explicitly states statement opacity has been the source of greatest unease; advisor responds with unbundled fee schedule.",
    status: "pending",
  },
  {
    id: "S-002", transcriptId: "TR-2041", type: "driver", rank: 2,
    category: "Advisor Trust",
    quote: "The personal introduction matters. The previous firm — it always felt like we were just an account number.",
    timestamp: "00:11:02",
    evidence: "explicit",
    rationale: "Direct contrast with prior advisor experience; trust is anchored to personal accountability on the estate desk introduction.",
    status: "approved",
  },
  {
    id: "S-003", transcriptId: "TR-2041", type: "driver", rank: 3,
    category: "Performance vs Benchmark",
    quote: "I trust the call. The transparency on where the return came from is — that's the difference from where we were before.",
    timestamp: "00:15:55",
    evidence: "explicit",
    rationale: "Trust is conditional on attribution clarity rather than headline return; suggests retention risk if attribution detail is removed.",
    status: "pending",
  },
  {
    id: "S-004", transcriptId: "TR-2041", type: "driver", rank: 4,
    category: "Reporting Quality",
    quote: "The old reports — we literally couldn't explain them to our son. He's the one who'd take this over eventually.",
    timestamp: "00:20:01",
    evidence: "explicit",
    rationale: "Reporting clarity is tied to multi-generational continuity; flag for the next-gen reporting initiative.",
    status: "pending",
  },
  {
    id: "S-005", transcriptId: "TR-2041", type: "driver", rank: 5,
    category: "Cash Flow Clarity",
    quote: "That alone — that single change — is meaningful. We had no idea.",
    timestamp: "00:26:08",
    evidence: "implied",
    rationale: "Reaction strength (\"that single change\") implies cash-yield education is a high-value, low-cost differentiator.",
    status: "pending",
  },
  {
    id: "S-006", transcriptId: "TR-2041", type: "blocker", rank: 1,
    category: "Statement Confusion",
    quote: "Every time I see the statement I'm not sure what I'm actually paying versus what's bundled.",
    timestamp: "00:01:48",
    evidence: "explicit",
    rationale: "Recurring confusion at statement-level — this is the dominant blocker and the trailing-fee surfacing is a partial remediation, not a fix.",
    status: "pending",
  },
  {
    id: "S-007", transcriptId: "TR-2041", type: "blocker", rank: 2,
    category: "Service Lapses",
    quote: "Two months to get a statement reissued. If something happens to me I don't want her going through that.",
    timestamp: "00:07:18",
    evidence: "explicit",
    rationale: "Concrete past failure (estate-desk reissue delay) is being carried into present-day anxiety about continuity.",
    status: "pending",
  },
  {
    id: "S-008", transcriptId: "TR-2041", type: "blocker", rank: 3,
    category: "Tax Drag",
    quote: "Last year we got hit harder than we expected on the non-registered side.",
    timestamp: "00:03:55",
    evidence: "implied",
    rationale: "Surprise on tax outcome implies upstream planning gap; advisor mitigates with staged rebalance but root cause is unresolved in transcript.",
    status: "pending",
  },
];

export const pipelineSteps: PipelineStep[] = [
  { step: 1, name: "Transcript preparation",    status: "ok", model: "haiku-4-5",  prompt: "prep@v3.2",    retries: 0, latency: "1.2s",  tokensIn: 18420, tokensOut: 1240, cost: 0.0094 },
  { step: 2, name: "Segment signal extraction",  status: "ok", model: "sonnet-4-5", prompt: "extract@v5.1", retries: 1, latency: "11.4s", tokensIn: 88240, tokensOut: 6010, cost: 0.1822 },
  { step: 3, name: "Consolidation & ranking",    status: "ok", model: "sonnet-4-5", prompt: "consol@v2.0",  retries: 0, latency: "6.8s",  tokensIn: 41200, tokensOut: 2811, cost: 0.0904 },
  { step: 4, name: "Evidence validation",        status: "ok", model: "haiku-4-5",  prompt: "verify@v1.4",  retries: 0, latency: "3.1s",  tokensIn: 28010, tokensOut: 1480, cost: 0.0612 },
  { step: 5, name: "Deterministic final formatting", status: "ok", model: "No model recorded", prompt: "No prompt recorded", retries: 0, latency: "Not tracked", tokensIn: 0, tokensOut: 0, cost: 0 },
];

export const activity: ActivityEntry[] = [
  { id: "TR-2041", who: "M. Okafor",    when: "12 min ago", action: "completed processing", n: 8 },
  { id: "TR-2040", who: "S. Devarajan", when: "2 h ago",    action: "approved 6 signals",   n: 6 },
  { id: "TR-2039", who: "R. Toussaint", when: "5 h ago",    action: "flagged for review",   n: 3 },
  { id: "TR-2038", who: "system",       when: "6 h ago",    action: "started processing",   n: 0 },
  { id: "TR-2036", who: "system",       when: "yesterday",  action: "failed at step 3",     n: 0 },
  { id: "TR-2037", who: "M. Okafor",    when: "yesterday",  action: "exported as JSONL",    n: 8 },
];
