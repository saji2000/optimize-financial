import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { BarRow, Btn, KPI, Money, Section, Sparkline, TopBar } from "../components/primitives";
import { useActivity, useTranscripts } from "../data/DataProvider";

export function DashboardPage() {
  const navigate = useNavigate();
  const transcripts = useTranscripts();
  const activity = useActivity();
  const total = transcripts.length;
  const by = (s: string) => transcripts.filter((t) => t.status === s).length;
  const backlog = transcripts.filter((t) => t.reviewState === "pending").length;
  const cost = transcripts.reduce((a, b) => a + b.cost, 0);
  const failedTranscript = transcripts.find((t) => t.status === "failed");

  const trend = useMemo(() => {
    const out: number[] = [];
    let v = 0.18;
    for (let i = 0; i < 14; i++) {
      v = Math.max(0.1, v + (Math.random() - 0.45) * 0.12);
      out.push(v);
    }
    return out;
  }, []);

  function openTranscript(id: string) {
    navigate(`/transcripts/${id}`);
  }

  return (
    <>
      <TopBar
        title="Dashboard"
        subtitle="Tuesday - May 20, 2026"
        right={
          <Btn kind="ghost" onClick={() => navigate("/transcripts")}>
            Open transcripts -&gt;
          </Btn>
        }
      />

      <div className="kpis">
        <KPI
          label="Transcripts"
          value={total}
          sub={`${by("completed")} completed - ${by("running")} running`}
        />
        <KPI
          label="Review backlog"
          value={backlog}
          sub="awaiting reviewer sign-off"
          accent="var(--amber)"
        />
        <KPI
          label="Failed runs (24h)"
          value={by("failed")}
          sub="see Pipeline runs for retries"
          accent="var(--rust)"
        />
        <KPI
          label="Est. cost (all time)"
          value={"$" + cost.toFixed(2)}
          sub={`avg $${(cost / Math.max(total, 1)).toFixed(3)}/transcript`}
        />
      </div>

      <div className="grid-2">
        <Section
          eyebrow="Pipeline health - 14 days"
          title="Cost per transcript"
          right={<span className="mono small">peak $0.51 - low $0.14</span>}
        >
          <div className="trendwrap">
            <Sparkline points={trend} w={620} h={120} />
            <div className="trend-axis">
              <span>May 7</span>
              <span>May 14</span>
              <span>May 20</span>
            </div>
          </div>
          <div className="legend">
            <span className="dot dot--ink" /> daily mean spend
            <span className="legend__sep">-</span>
            <span className="mono">avg ${(cost / Math.max(total, 1)).toFixed(3)}</span>
          </div>
        </Section>

        <Section eyebrow="Status breakdown" title="Pipeline state">
          <BarRow label="completed" value={by("completed")} max={Math.max(total, 1)} color="var(--moss)" />
          <BarRow label="running" value={by("running")} max={Math.max(total, 1)} color="var(--amber)" />
          <BarRow label="queued" value={by("queued")} max={Math.max(total, 1)} color="var(--slate)" />
          <BarRow label="failed" value={by("failed")} max={Math.max(total, 1)} color="var(--rust)" />
          {failedTranscript && (
            <div className="callout">
              <span className="dot dot--rust" />
              <div>
                <b>{failedTranscript.id}</b> failed during processing. Reviewer attention recommended.
                <button className="link" onClick={() => openTranscript(failedTranscript.id)}>
                  Open run -&gt;
                </button>
              </div>
            </div>
          )}
        </Section>
      </div>

      <div className="grid-2">
        <Section eyebrow="Recent" title="Activity">
          <ul className="activity">
            {activity.map((a, i) => (
              <li key={i} className="activity__row">
                <span className="mono activity__id">{a.id}</span>
                <span className="activity__who">{a.who}</span>
                <span className="activity__action">
                  {a.action}
                  {a.n ? <em className="activity__n"> - {a.n}</em> : null}
                </span>
                <span className="activity__when">{a.when}</span>
                <button className="link" onClick={() => openTranscript(a.id)}>
                  view -&gt;
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <Section eyebrow="Today's queue" title="Needs reviewer attention">
          <table className="t">
            <thead>
              <tr>
                <th>Transcript</th>
                <th>Drivers</th>
                <th>Blockers</th>
                <th>Cost</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {transcripts
                .filter((t) => t.reviewState === "pending")
                .map((t) => (
                  <tr key={t.id}>
                    <td>
                      <div className="mono small">{t.id}</div>
                      <div>{t.name}</div>
                    </td>
                    <td className="mono">{t.drivers}</td>
                    <td className="mono">{t.blockers}</td>
                    <td>
                      <Money value={t.cost} />
                    </td>
                    <td>
                      <button className="link" onClick={() => openTranscript(t.id)}>
                        review -&gt;
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </Section>
      </div>
    </>
  );
}
