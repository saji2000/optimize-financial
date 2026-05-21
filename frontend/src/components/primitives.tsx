import { ReactNode, CSSProperties } from "react";
import type { TranscriptStatus, ReviewState, SignalType, EvidenceKind, SignalStatus } from "../data/mockData";

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-label="Optimize Financial">
      <rect x="2" y="2" width="60" height="60" rx="12" fill="var(--ink)" />
      <circle cx="32" cy="32" r="20" stroke="var(--paper)" strokeWidth="2.5" fill="none" />
      <path d="M32 12 L36 32 L32 52 L28 32 Z" fill="var(--paper)" />
      <circle cx="32" cy="32" r="2.2" fill="var(--ink)" />
    </svg>
  );
}

export function Wordmark({ size = 18 }: { size?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <Logo size={size + 12} />
      <div style={{ lineHeight: 1, display: "flex", flexDirection: "column", gap: 2 }}>
        <div
          style={{
            fontFamily: "Newsreader, Georgia, serif",
            fontSize: size + 4,
            fontWeight: 500,
            letterSpacing: "-0.01em",
            color: "var(--ink)",
          }}
        >
          Optimize<span style={{ fontStyle: "italic", opacity: 0.7 }}>·</span>
        </div>
        <div
          style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: 9.5,
            fontWeight: 500,
            letterSpacing: "0.18em",
            color: "var(--slate)",
            textTransform: "uppercase",
          }}
        >
          Financial Review
        </div>
      </div>
    </div>
  );
}

export function StatusPill({ status }: { status: TranscriptStatus | string }) {
  const map: Record<string, { c: string; label: string }> = {
    completed: { c: "moss", label: "completed" },
    running: { c: "amber", label: "running" },
    queued: { c: "slate", label: "queued" },
    failed: { c: "rust", label: "failed" },
  };
  const s = map[status] || { c: "slate", label: status };
  return (
    <span className={"pill pill--" + s.c}>
      <span className="pill__dot" />
      {s.label}
    </span>
  );
}

export function ReviewPill({ state }: { state: ReviewState | SignalStatus | string }) {
  const map: Record<string, { c: string; label: string }> = {
    pending: { c: "amber", label: "pending review" },
    approved: { c: "moss", label: "approved" },
    rejected: { c: "rust", label: "rejected" },
    "—": { c: "ghost", label: "—" },
  };
  const s = map[state] || { c: "ghost", label: String(state) };
  return <span className={"pill pill--" + s.c}>{s.label}</span>;
}

export function EvidencePill({ kind }: { kind: EvidenceKind }) {
  if (kind === "explicit") return <span className="tag tag--ink">explicit</span>;
  return <span className="tag tag--ghost">implied</span>;
}

export function TypePill({ type }: { type: SignalType }) {
  if (type === "driver") return <span className="tag tag--moss">▲ driver</span>;
  return <span className="tag tag--rust">▼ blocker</span>;
}

export function Money({ value, big }: { value: number | null | undefined; big?: boolean }) {
  if (value == null) return <span className="mono">—</span>;
  return <span className={"mono " + (big ? "money money--big" : "money")}>${value.toFixed(4)}</span>;
}

export function Tok({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="mono">—</span>;
  return <span className="mono">{value.toLocaleString()}</span>;
}

export function Sparkline({
  points,
  color = "var(--ink)",
  w = 240,
  h = 56,
}: {
  points: number[];
  color?: string;
  w?: number;
  h?: number;
}) {
  if (!points || !points.length) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const pad = 2;
  const xs = (i: number) => pad + (i * (w - pad * 2)) / (points.length - 1);
  const ys = (v: number) => h - pad - ((v - min) / Math.max(0.0001, max - min)) * (h - pad * 2);
  const d = points.map((v, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(" ");
  const area = `${d} L${xs(points.length - 1).toFixed(1)},${h} L${xs(0).toFixed(1)},${h} Z`;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <path d={area} fill={color} opacity="0.08" />
      <path d={d} stroke={color} strokeWidth="1.4" fill="none" />
    </svg>
  );
}

export function BarRow({
  label,
  value,
  max,
  color = "var(--ink)",
}: {
  label: ReactNode;
  value: number;
  max: number;
  color?: string;
}) {
  const pct = Math.max(0.02, value / max);
  return (
    <div className="barrow">
      <div className="barrow__label">{label}</div>
      <div className="barrow__track">
        <div
          className="barrow__fill"
          style={{ width: (pct * 100).toFixed(1) + "%", background: color }}
        />
      </div>
      <div className="barrow__value mono">
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
    </div>
  );
}

export function Section({
  eyebrow,
  title,
  right,
  children,
}: {
  eyebrow?: ReactNode;
  title?: ReactNode;
  right?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="section">
      <header className="section__head">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          {title && <h2 className="section__title">{title}</h2>}
        </div>
        {right && <div>{right}</div>}
      </header>
      <div>{children}</div>
    </section>
  );
}

export function KPI({
  label,
  value,
  sub,
  accent,
}: {
  label: ReactNode;
  value: ReactNode;
  sub?: ReactNode;
  accent?: string;
}) {
  const style: CSSProperties = { color: accent || "var(--ink)" };
  return (
    <div className="kpi">
      <div className="kpi__label">{label}</div>
      <div className="kpi__value" style={style}>
        {value}
      </div>
      {sub && <div className="kpi__sub">{sub}</div>}
    </div>
  );
}

export function Field({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
    </label>
  );
}

export function Btn({
  children,
  kind = "primary",
  onClick,
  full,
  type,
  disabled,
}: {
  children: ReactNode;
  kind?: "primary" | "ghost";
  onClick?: () => void;
  full?: boolean;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
}) {
  return (
    <button
      type={type || "button"}
      className={"btn btn--" + kind + (full ? " btn--full" : "")}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function TopBar({
  title,
  subtitle,
  right,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="topbar">
      <div>
        <h1 className="topbar__title">{title}</h1>
        {subtitle && <div className="topbar__sub">{subtitle}</div>}
      </div>
      <div className="topbar__right">{right}</div>
    </div>
  );
}
