interface EvidenceQuoteProps {
  quote: string;
}

export function EvidenceQuote({ quote }: EvidenceQuoteProps) {
  return <blockquote className="evidence-quote">{quote}</blockquote>;
}

