export function canReviewSignals(role: string) {
  return role === "admin" || role === "reviewer";
}

