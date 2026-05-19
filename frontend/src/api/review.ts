export interface ReviewDecisionRequest {
  signalId: string;
  decision: "approve" | "reject";
  notes?: string;
}

