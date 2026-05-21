import { useNavigate, useParams } from "react-router-dom";
import {
  BarRow,
  Btn,
  KPI,
  Money,
  Section,
  TopBar,
} from "../components/primitives";
import { pipelineSteps, transcripts } from "../data/mockData";

export function PipelineRunPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const transcript = transcripts.find((x) => x.id === id) || transcripts[0];
  const steps = pipelineSteps;
  const total = steps.reduce((a, b) => a + b.cost, 0);
  const totalIn = steps.reduce((a, b) => a + b.tokensIn, 0);
  const totalOut = steps.reduce((a, b) => a + b.tokensOut, 0);

  return (
    <>
      <TopBar
        title={`Pipeline run · ${transcript.id}`}
        subtitle={
          <>
            {transcript.name} · 5-step workflow · <Money value={total} /> total
          </>
        }
        right={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn kind="ghost" onClick={() => navigate("/transcripts")}>
              ← Back to library
            </Btn>
            <Btn kind="ghost" onClick={() => navigate(`/transcripts/${transcript.id}`)}>
              Transcript detail →
            </Btn>
          </div>
        }
      />

      <div className="kpis">
        <KPI label="Total run cost" value={"$" + total.toFixed(4)} sub="all 5 steps" />
        <KPI label="Latency · end-to-end" value="24.9s" sub="step-2 dominant" />
        <KPI
          label="Tokens · in / out"
          value={`${(totalIn / 1000).toFixed(1)}K / ${(totalOut / 1000).toFixed(1)}K`}
        />
        <KPI
          label="Retries · this run"
          value={steps.reduce((a, b) => a + b.retries, 0)}
          sub="step-2 auto-retried 1x"
          accent="var(--amber)"
        />
      </div>

      <Section eyebrow="5-step workflow" title="Agent run timeline">
        <ol className="pipe">
          {steps.map((s, i) => (
            <li key={s.step} className={"pipe__step pipe__step--" + s.status}>
              <div className="pipe__num">
                <span className="mono">{s.step}</span>
              </div>
              <div className="pipe__body">
                <div className="pipe__head">
                  <h3 className="pipe__title">{s.name}</h3>
                  <span className={"tag " + (s.status === "ok" ? "tag--moss" : "tag--rust")}>
                    {s.status === "ok" ? "completed" : "failed"}
                  </span>
                </div>
                <dl className="pipe__grid">
                  <div><dt>Model</dt><dd className="mono">{s.model}</dd></div>
                  <div><dt>Prompt</dt><dd className="mono">{s.prompt}</dd></div>
                  <div><dt>Retries</dt><dd className="mono">{s.retries}</dd></div>
                  <div><dt>Latency</dt><dd className="mono">{s.latency}</dd></div>
                  <div><dt>Tokens in</dt><dd className="mono">{s.tokensIn.toLocaleString()}</dd></div>
                  <div><dt>Tokens out</dt><dd className="mono">{s.tokensOut.toLocaleString()}</dd></div>
                  <div><dt>Cost</dt><dd><Money value={s.cost} /></dd></div>
                </dl>
                {s.step === 2 && s.retries > 0 && (
                  <div className="callout callout--soft">
                    <span className="dot dot--amber" />
                    <div>
                      <b>Retry:</b> initial response failed schema validation on the `evidence`
                      field; auto-retried with stricter system prompt and recovered. No
                      transcript text exposed in this view.
                    </div>
                  </div>
                )}
                {i === steps.length - 1 && (
                  <div className="pipe__final">
                    <span className="eyebrow">Output</span> Agent 5 produced{" "}
                    <b>{transcript.drivers}</b> drivers and <b>{transcript.blockers}</b> blockers ·{" "}
                    <button
                      className="link"
                      onClick={() => navigate(`/transcripts/${transcript.id}`)}
                    >
                      review final output →
                    </button>
                  </div>
                )}
              </div>
              <div className="pipe__cost">
                <Money value={s.cost} />
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section eyebrow="Cost composition" title="Step-by-step share of run">
        {steps.map((s) => (
          <BarRow
            key={s.step}
            label={
              <span>
                <span className="mono small slate">{s.step}.</span> {s.name}
              </span>
            }
            value={Number(s.cost.toFixed(4))}
            max={Math.max(...steps.map((x) => x.cost))}
            color={s.step === 2 ? "var(--ink)" : "var(--slate)"}
          />
        ))}
      </Section>
    </>
  );
}
