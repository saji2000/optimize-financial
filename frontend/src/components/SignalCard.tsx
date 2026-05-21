import { useState } from "react";
import { EvidencePill, ReviewPill } from "./primitives";
import type { Signal } from "../data/mockData";

interface Props {
  s: Signal;
  onJump?: () => void;
  onHover?: () => void;
  onLeave?: () => void;
  onUpdate: (patch: Partial<Signal>) => void;
}

export function SignalCard({ s, onJump, onHover, onLeave, onUpdate }: Props) {
  const [editingCat, setEditingCat] = useState(false);
  const [cat, setCat] = useState(s.category);
  const [rat, setRat] = useState(s.rationale);
  const [editingRat, setEditingRat] = useState(false);

  function saveCat() {
    setEditingCat(false);
    onUpdate({ category: cat });
  }
  function saveRat() {
    setEditingRat(false);
    onUpdate({ rationale: rat });
  }

  return (
    <article
      className={"signal signal--" + s.type + " signal--" + s.status}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      <header className="signal__head">
        <div className="signal__rank">
          <span className="mono small slate">rank</span>
          <span className="signal__rank-n">{s.rank}</span>
        </div>
        <div className="signal__title">
          {editingCat ? (
            <input
              className="input input--inline"
              value={cat}
              onChange={(e) => setCat(e.target.value)}
              onBlur={saveCat}
              onKeyDown={(e) => e.key === "Enter" && saveCat()}
              autoFocus
            />
          ) : (
            <button
              className="signal__cat"
              onClick={() => setEditingCat(true)}
              title="edit category"
            >
              {cat}
            </button>
          )}
          <div className="signal__meta">
            <button
              className="signal__ts mono"
              onClick={onJump}
              title="jump to transcript"
            >
              ⤴ {s.timestamp}
            </button>
            <EvidencePill kind={s.evidence} />
            <ReviewPill state={s.status} />
          </div>
        </div>
      </header>

      <blockquote className="signal__quote" onClick={onJump}>
        <span className="signal__qmark">“</span>
        {s.quote}
        <span className="signal__qmark">”</span>
      </blockquote>

      <div className="signal__rat">
        <span className="lbl">Rationale</span>
        {editingRat ? (
          <textarea
            className="input input--area"
            value={rat}
            onChange={(e) => setRat(e.target.value)}
            onBlur={saveRat}
            autoFocus
            rows={3}
          />
        ) : (
          <p onClick={() => setEditingRat(true)} title="click to edit">
            {rat}
          </p>
        )}
      </div>

      <footer className="signal__actions">
        <button
          className={"sbtn " + (s.status === "approved" ? "sbtn--on sbtn--ok" : "")}
          onClick={() =>
            onUpdate({ status: s.status === "approved" ? "pending" : "approved" })
          }
        >
          ✓ approve
        </button>
        <button
          className={"sbtn " + (s.status === "rejected" ? "sbtn--on sbtn--bad" : "")}
          onClick={() =>
            onUpdate({ status: s.status === "rejected" ? "pending" : "rejected" })
          }
        >
          ✕ reject
        </button>
        <button
          className={"sbtn " + (s.flag ? "sbtn--on sbtn--flag" : "")}
          onClick={() => onUpdate({ flag: !s.flag })}
        >
          ⚑ follow-up
        </button>
        <button className="sbtn" onClick={() => setEditingCat(true)}>
          ✎ edit category
        </button>
      </footer>
    </article>
  );
}
