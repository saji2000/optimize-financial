import { ReactNode, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Btn,
  Money,
  ReviewPill,
  StatusPill,
  TopBar,
} from "../components/primitives";
import { SignalCard } from "../components/SignalCard";
import { Signal } from "../data/mockData";
import { useTranscriptDetail } from "../data/DataProvider";
import { useSignals } from "../data/SignalsStore";

function renderTurnText(
  text: string,
  quotedSignals: Signal[],
  hoverId: string | null,
  focusId: string | null,
): ReactNode {
  if (!quotedSignals || quotedSignals.length === 0) return text;
  const target = quotedSignals[0];
  const idx = text.indexOf(target.quote);
  if (idx === -1) return text;
  const before = text.slice(0, idx);
  const after = text.slice(idx + target.quote.length);
  const isHL = quotedSignals.some((s) => s.id === hoverId || s.id === focusId);
  return (
    <>
      {before}
      <mark className={"quote " + (isHL ? "quote--hl" : "")}>{target.quote}</mark>
      {after}
    </>
  );
}

export function TranscriptDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { transcript, turns } = useTranscriptDetail(id);
  const { signalsForTranscript, updateSignal } = useSignals();
  const signals = signalsForTranscript(transcript?.id || id);

  const [activeTs, setActiveTs] = useState<string | null>(null);
  const [hoverQuote, setHoverQuote] = useState<string | null>(null);
  const [focusSignalId, setFocusSignalId] = useState<string | null>(null);
  const turnRefs = useRef<Record<string, HTMLDivElement | null>>({});

  function jumpTo(ts: string, signalId: string) {
    setActiveTs(ts);
    setFocusSignalId(signalId);
    const el = turnRefs.current[ts];
    if (el && el.parentElement) {
      el.parentElement.scrollTop = el.offsetTop - 80;
    }
    setTimeout(() => setActiveTs(null), 1800);
  }

  const drivers = signals.filter((s) => s.type === "driver").sort((a, b) => a.rank - b.rank);
  const blockers = signals.filter((s) => s.type === "blocker").sort((a, b) => a.rank - b.rank);

  if (!transcript) {
    return (
      <TopBar
        title="Transcript not found"
        subtitle="No backend or mock row is available for this id"
        right={<Btn kind="ghost" onClick={() => navigate("/transcripts")}>Back to library</Btn>}
      />
    );
  }

  return (
    <>
      <TopBar
        title={transcript.name}
        subtitle={
          <>
            <span className="mono small">{transcript.id}</span> · {transcript.client} · advisor{" "}
            {transcript.advisor} · {transcript.duration}
          </>
        }
        right={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn kind="ghost" onClick={() => navigate("/transcripts")}>
              ← Back to library
            </Btn>
            <Btn kind="ghost" onClick={() => navigate(`/pipeline/${transcript.id}`)}>
              Pipeline run →
            </Btn>
            <Btn>Export .jsonl</Btn>
          </div>
        }
      />

      <div className="detail-meta">
        <div className="dmeta">
          <span className="eyebrow">Status</span>
          <StatusPill status={transcript.status} />
        </div>
        <div className="dmeta">
          <span className="eyebrow">Review</span>
          <ReviewPill state={transcript.reviewState} />
        </div>
        <div className="dmeta">
          <span className="eyebrow">Final signals</span>
          <span className="strong">
            <span className="mono">{drivers.length}</span> drivers ·{" "}
            <span className="mono">{blockers.length}</span> blockers
          </span>
        </div>
        <div className="dmeta">
          <span className="eyebrow">Cost</span>
          <Money value={transcript.cost} big />
        </div>
        <div className="dmeta">
          <span className="eyebrow">Tokens in / out</span>
          <span className="mono">
            {transcript.tokensIn.toLocaleString()} / {transcript.tokensOut.toLocaleString()}
          </span>
        </div>
        <div className="dmeta">
          <span className="eyebrow">Model calls</span>
          <span className="mono">
            {transcript.calls} · {transcript.retries} retries
          </span>
        </div>
      </div>

      <div className="detail">
        <div className="card detail__transcript">
          <div className="card__head">
            <div className="eyebrow">Transcript · speaker turns</div>
            <div className="small slate">click any timestamp on the right to jump here</div>
          </div>
          <div className="turns">
            {turns.map((turn, i) => {
              const isActive = activeTs === turn.t;
              const isQuoted = signals.some((s) => s.timestamp === turn.t);
              return (
                <div
                  key={i}
                  ref={(el) => {
                    turnRefs.current[turn.t] = el;
                  }}
                  className={
                    "turn " +
                    (turn.who === "Advisor" ? "turn--adv" : "turn--cli") +
                    (isActive ? " turn--flash" : "") +
                    (isQuoted ? " turn--quoted" : "")
                  }
                >
                  <div className="turn__rail">
                    <span className="mono small slate">{turn.t}</span>
                    <span className="turn__who">{turn.who}</span>
                    <span className="small slate">{turn.name}</span>
                  </div>
                  <p className="turn__text">
                    {renderTurnText(
                      turn.text,
                      signals.filter((s) => s.timestamp === turn.t),
                      hoverQuote,
                      focusSignalId,
                    )}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="detail__output">
          <div className="agent5-head">
            <div>
              <div className="eyebrow">Final · Agent 5</div>
              <h2 className="agent5-title">
                Drivers <span className="slate">/</span> Blockers
              </h2>
            </div>
            <span className="tag tag--ink">public-facing</span>
          </div>

          <div className="signal-group">
            <div className="signal-group__head">
              <span className="tag tag--moss">▲ Drivers</span>
              <span className="mono small slate">{drivers.length} ranked</span>
            </div>
            {drivers.map((s) => (
              <SignalCard
                key={s.id}
                s={s}
                onJump={() => jumpTo(s.timestamp, s.id)}
                onHover={() => setHoverQuote(s.id)}
                onLeave={() => setHoverQuote(null)}
                onUpdate={(patch) => updateSignal(s.id, patch)}
              />
            ))}
          </div>

          <div className="signal-group">
            <div className="signal-group__head">
              <span className="tag tag--rust">▼ Blockers</span>
              <span className="mono small slate">{blockers.length} ranked</span>
            </div>
            {blockers.map((s) => (
              <SignalCard
                key={s.id}
                s={s}
                onJump={() => jumpTo(s.timestamp, s.id)}
                onHover={() => setHoverQuote(s.id)}
                onLeave={() => setHoverQuote(null)}
                onUpdate={(patch) => updateSignal(s.id, patch)}
              />
            ))}
          </div>

          <div className="cost-summary">
            <div className="eyebrow">Cost summary · this transcript</div>
            <div className="cost-summary__grid">
              <div>
                <span className="lbl">Total</span>
                <Money value={transcript.cost} big />
              </div>
              <div>
                <span className="lbl">Tokens in</span>
                <span className="mono">{transcript.tokensIn.toLocaleString()}</span>
              </div>
              <div>
                <span className="lbl">Tokens out</span>
                <span className="mono">{transcript.tokensOut.toLocaleString()}</span>
              </div>
              <div>
                <span className="lbl">Calls</span>
                <span className="mono">{transcript.calls}</span>
              </div>
            </div>
            <button className="link" onClick={() => navigate(`/pipeline/${transcript.id}`)}>
              see cost by pipeline step →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
