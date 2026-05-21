import { KPI, Money, Section, TopBar } from "../components/primitives";
import { pipelineSteps, transcripts } from "../data/mockData";

export function AnalyticsPage() {
  const stepTotals = pipelineSteps.map((s) => ({ ...s }));
  const sumCost = stepTotals.reduce((a, b) => a + b.cost, 0);
  const sumIn = stepTotals.reduce((a, b) => a + b.tokensIn, 0);
  const sumOut = stepTotals.reduce((a, b) => a + b.tokensOut, 0);
  const totalSpend = transcripts.reduce((a, b) => a + b.cost, 0);

  const mix = [
    { model: "claude-sonnet-4-5", share: 0.62, color: "var(--ink)" },
    { model: "claude-haiku-4-5", share: 0.34, color: "var(--moss)" },
    { model: "embed-v3 (rerank)", share: 0.04, color: "var(--amber)" },
  ];

  return (
    <>
      <TopBar title="Cost & usage" subtitle="Aggregate spend across the 5-step pipeline" />
      <div className="kpis">
        <KPI
          label="Total spend · all time"
          value={"$" + totalSpend.toFixed(2)}
          sub={`${transcripts.length} transcripts`}
        />
        <KPI
          label="Avg per transcript"
          value={"$" + (totalSpend / transcripts.length).toFixed(3)}
          sub="trending –12% MoM"
          accent="var(--moss)"
        />
        <KPI
          label="Tokens (in / out)"
          value={`${(sumIn / 1000).toFixed(0)}K / ${(sumOut / 1000).toFixed(1)}K`}
          sub="per representative transcript"
        />
        <KPI
          label="Retry rate"
          value="6.3%"
          sub="3 of 47 step-runs retried"
          accent="var(--amber)"
        />
      </div>

      <div className="grid-2 grid-2--asym">
        <Section
          eyebrow="Per-step cost · representative transcript"
          title="Where the money goes"
        >
          <table className="t">
            <thead>
              <tr>
                <th>Step</th>
                <th>Model</th>
                <th className="num">In</th>
                <th className="num">Out</th>
                <th className="num">Retries</th>
                <th className="num">Cost</th>
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
                <td colSpan={5}><b>Total per transcript</b></td>
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
            <b>Reliability:</b> 3 retries across 47 step runs (6.3%). All retries auto-fell-back
            to haiku and recovered. Net cost impact: <span className="mono">+$0.041</span>.
          </div>
        </Section>
      </div>
    </>
  );
}
