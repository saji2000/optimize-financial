import { SignalCard } from "../components/SignalCard";

export function SignalReviewPage() {
  return (
    <section className="page">
      <div className="page-header">
        <h1>Review queue</h1>
        <p>Approve or reject extracted signals before representative release.</p>
      </div>
      <div className="card-grid">
        <SignalCard />
      </div>
    </section>
  );
}

