import { KPI, Money, Section, TopBar } from "../components/primitives";
import { usePipelineSteps, useTranscripts } from "../data/DataProvider";

export function AnalyticsPage() {
  const transcripts = useTranscripts();
  const representative = transcripts.find((t) => t.calls > 0) || transcripts[0];
  const stepTotals = usePipelineSteps(representative?.id).map((s) => ({ ...s }));
  const sumCost = stepTotals.reduce((a, b) => a + b.cost, 0);
  const sumIn = stepTotals.reduce((a, b) => a + b.tokensIn, 0);
  const sumOut = stepTotals.reduce((a, b) => a + b.tokensOut, 0);
  const totalSpend = transcripts.reduce((a, b) => a + b.cost, 0);
  const retries = stepTotals.reduce((a, b) => a + b.retries, 0);

  const mix = stepTotals.map((s, index) => ({
    model: s.model,
    share: sumCost > 0 ? s.cost / sumCost : 0,
    color: index === 0 ? "var(--ink)" : index === 1 ? "var(--moss)" : "var(--amber)",
  }));

  return (
    <>
      <TopBar title="Cost & usage" subtitle="Estimated API cost from recorded LLM usage" />
      <div className="kpis">
        <KPI
          label="Estimated LLM cost"
          value={"$" + totalSpend.toFixed(2)}
          sub={`${transcripts.length} transcripts`}
        />
        <KPI
          label="Avg per transcript"
          value={"$" + (totalSpend / Math.max(transcripts.length, 1)).toFixed(3)}
          sub="from backend usage events"
          accent="var(--moss)"
        />
        <KPI
          label="Tokens (in / out)"
          value={`${(sumIn / 1000).toFixed(0)}K / ${(sumOut / 1000).toFixed(1)}K`}
          sub={stepTotals.length ? "representative transcript" : "No usage recorded yet"}
        />
        <KPI
          label="Retries"
          value={retries}
          sub={stepTotals.length ? "recorded retries" : "No usage recorded yet"}
          accent="var(--amber)"
        />
      </div>

      <div className="grid-2 grid-2--asym">
        <Section
          eyebrow="Estimated per-step API cost · representative transcript"
          title="Where the money goes"
        >
          {stepTotals.length === 0 && (
            <div className="empty">No usage recorded yet.</div>
          )}
          <table className="t">
            <thead>
              <tr>
                <th>Step</th>
                <th>Model</th>
                <th className="num">In</th>
                <th className="num">Out</th>
                <th className="num">Retries</th>
                <th className="num">Estimated cost</th>
              </tr>
            </thead>
            <tbody>
              {stepTotals.map((s) => (
                <tr key={s.step}>
                  <td>
                    <span className="step-num mono">{s.step}</span> {s.name}
                  </td>
                  <td><span className="tag tag--ghost mono">{s.model}</span></td>
                  <td className="num mono">{s.tokensIn.toLocaleString()}</td>
                  <td className="num mono">{s.tokensOut.toLocaleString()}</td>
                  <td className="num mono">{s.retries}</td>
                  <td className="num"><Money value={s.cost} /></td>
                </tr>
              ))}
              <tr className="row-sum">
                <td colSpan={5}><b>Estimated total per transcript</b></td>
                <td className="num"><Money value={sumCost} big /></td>
              </tr>
            </tbody>
          </table>
        </Section>

        <Section eyebrow="Model mix" title="Across the workflow">
          <div className="mix">
            {mix.map((m) => (
              <div key={m.model} className="mix__row">
                <div className="mix__head">
                  <span className="mono small">{m.model}</span>
                  <span className="mono small">{(m.share * 100).toFixed(0)}%</span>
                </div>
                <div className="barrow__track">
                  <div
                    className="barrow__fill"
                    style={{ width: m.share * 100 + "%", background: m.color }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="callout callout--soft">
            <b>Reliability:</b> retry counts are summed from persisted LLM usage events.
            Estimated cost is calculated by the backend pricing table, not invoice data.
          </div>
        </Section>
      </div>
    </>
  );
}
