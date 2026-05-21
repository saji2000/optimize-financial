import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  EvidencePill,
  ReviewPill,
  TopBar,
  TypePill,
} from "../components/primitives";
import { useSignals } from "../data/SignalsStore";

export function SignalReviewPage() {
  const { signals, updateSignal } = useSignals();
  const navigate = useNavigate();
  const [type, setType] = useState("all");
  const [cat, setCat] = useState("all");
  const [ev, setEv] = useState("all");
  const [stat, setStat] = useState("all");
  const [view, setView] = useState<"cards" | "table">("cards");

  const cats = useMemo(
    () => Array.from(new Set(signals.map((s) => s.category))).sort(),
    [signals],
  );

  const rows = signals.filter(
    (s) =>
      (type === "all" || s.type === type) &&
      (cat === "all" || s.category === cat) &&
      (ev === "all" || s.evidence === ev) &&
      (stat === "all" || s.status === stat),
  );

  const counts = {
    pending: signals.filter((s) => s.status === "pending").length,
    approved: signals.filter((s) => s.status === "approved").length,
    rejected: signals.filter((s) => s.status === "rejected").length,
  };

  return (
    <>
      <TopBar
        title="Signal review"
        subtitle={`${signals.length} Agent-5 signals · ${counts.pending} pending · ${counts.approved} approved · ${counts.rejected} rejected`}
        right={
          <div className="seg">
            <button
              className={"seg__opt " + (view === "cards" ? "seg__opt--on" : "")}
              onClick={() => setView("cards")}
            >
              cards
            </button>
            <button
              className={"seg__opt " + (view === "table" ? "seg__opt--on" : "")}
              onClick={() => setView("table")}
            >
              table
            </button>
          </div>
        }
      />

      <div className="toolbar">
        <div className="toolbar__group">
          <label className="lbl">Type</label>
          <div className="seg">
            {["all", "driver", "blocker"].map((o) => (
              <button
                key={o}
                className={"seg__opt " + (type === o ? "seg__opt--on" : "")}
                onClick={() => setType(o)}
              >
                {o}
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar__group">
          <label className="lbl">Category</label>
          <select className="select" value={cat} onChange={(e) => setCat(e.target.value)}>
            <option value="all">all</option>
            {cats.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="toolbar__group">
          <label className="lbl">Evidence</label>
          <div className="seg">
            {["all", "explicit", "implied"].map((o) => (
              <button
                key={o}
                className={"seg__opt " + (ev === o ? "seg__opt--on" : "")}
                onClick={() => setEv(o)}
              >
                {o}
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar__group">
          <label className="lbl">Status</label>
          <select className="select" value={stat} onChange={(e) => setStat(e.target.value)}>
            <option value="all">all</option>
            <option value="pending">pending</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
        </div>
      </div>

      {view === "cards" ? (
        <div className="review-grid">
          {rows.map((s) => (
            <article key={s.id} className={"signal signal--" + s.type + " signal--" + s.status}>
              <header className="signal__head">
                <div className="signal__rank">
                  <span className="mono small slate">rank</span>
                  <span className="signal__rank-n">{s.rank}</span>
                </div>
                <div className="signal__title">
                  <button className="signal__cat">{s.category}</button>
                  <div className="signal__meta">
                    <TypePill type={s.type} />
                    <EvidencePill kind={s.evidence} />
                    <ReviewPill state={s.status} />
                  </div>
                </div>
              </header>
              <blockquote className="signal__quote">
                <span className="signal__qmark">“</span>
                {s.quote}
                <span className="signal__qmark">”</span>
              </blockquote>
              <div className="signal__rat">
                <span className="lbl">Rationale</span>
                <p>{s.rationale}</p>
              </div>
              <footer className="signal__actions">
                <button
                  className={"sbtn " + (s.status === "approved" ? "sbtn--on sbtn--ok" : "")}
                  onClick={() =>
                    updateSignal(s.id, {
                      status: s.status === "approved" ? "pending" : "approved",
                    })
                  }
                >
                  ✓ approve
                </button>
                <button
                  className={"sbtn " + (s.status === "rejected" ? "sbtn--on sbtn--bad" : "")}
                  onClick={() =>
                    updateSignal(s.id, {
                      status: s.status === "rejected" ? "pending" : "rejected",
                    })
                  }
                >
                  ✕ reject
                </button>
                <button
                  className={"sbtn " + (s.flag ? "sbtn--on sbtn--flag" : "")}
                  onClick={() => updateSignal(s.id, { flag: !s.flag })}
                >
                  ⚑ follow-up
                </button>
                <button className="sbtn" onClick={() => navigate("/transcripts/TR-2041")}>
                  open in context →
                </button>
              </footer>
            </article>
          ))}
          {rows.length === 0 && (
            <div className="empty card">No signals match these filters.</div>
          )}
        </div>
      ) : (
        <div className="card">
          <table className="t">
            <thead>
              <tr>
                <th>Type</th>
                <th className="num">Rank</th>
                <th>Category</th>
                <th>Quote</th>
                <th className="num">Time</th>
                <th>Evidence</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td><TypePill type={s.type} /></td>
                  <td className="num mono">{s.rank}</td>
                  <td><b>{s.category}</b></td>
                  <td className="quote-cell">“{s.quote}”</td>
                  <td className="num mono">{s.timestamp}</td>
                  <td><EvidencePill kind={s.evidence} /></td>
                  <td><ReviewPill state={s.status} /></td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="iconbtn"
                        title="approve"
                        onClick={() =>
                          updateSignal(s.id, {
                            status: s.status === "approved" ? "pending" : "approved",
                          })
                        }
                      >
                        ✓
                      </button>
                      <button
                        className="iconbtn"
                        title="reject"
                        onClick={() =>
                          updateSignal(s.id, {
                            status: s.status === "rejected" ? "pending" : "rejected",
                          })
                        }
                      >
                        ✕
                      </button>
                      <button
                        className="iconbtn"
                        title="follow-up"
                        onClick={() => updateSignal(s.id, { flag: !s.flag })}
                      >
                        ⚑
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
