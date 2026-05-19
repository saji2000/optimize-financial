import { Check, X } from "lucide-react";

import { EvidenceQuote } from "./EvidenceQuote";

export function SignalCard() {
  return (
    <article className="card">
      <div className="card-header">
        <span className="eyebrow">Driver</span>
        <strong>Practice fit</strong>
      </div>
      <p>Advisor values tools that are easy to explain to clients.</p>
      <EvidenceQuote quote="The story has to be easy to explain to clients." />
      <div className="button-row">
        <button type="button" aria-label="Approve signal">
          <Check size={16} />
        </button>
        <button type="button" aria-label="Reject signal">
          <X size={16} />
        </button>
      </div>
    </article>
  );
}

