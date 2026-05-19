import { SignalTable } from "../components/SignalTable";

export function DashboardPage() {
  return (
    <section className="page">
      <div className="page-header">
        <h1>Advisor signals</h1>
        <p>Finalized drivers and blockers ready for representative review.</p>
      </div>
      <SignalTable />
    </section>
  );
}

