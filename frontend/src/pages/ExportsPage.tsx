import { useEffect, useMemo, useState } from "react";
import { Btn, Field, Section, TopBar } from "../components/primitives";
import { useTranscripts } from "../data/DataProvider";
import { useSignals } from "../data/SignalsStore";

export function ExportsPage() {
  const { signals } = useSignals();
  const transcripts = useTranscripts();
  const [scope, setScope] = useState<"all" | "one">("all");
  const [fmt, setFmt] = useState<"csv" | "json" | "jsonl">("jsonl");
  const [pickId, setPickId] = useState("TR-2041");

  const ready = transcripts.filter((t) => t.exportReady);
  const target =
    scope === "all" ? ready : transcripts.filter((t) => t.id === pickId);
  const targetIds = useMemo(() => new Set(target.map((t) => t.id)), [target]);

  useEffect(() => {
    if (!ready.some((t) => t.id === pickId) && ready[0]) {
      setPickId(ready[0].id);
    }
  }, [pickId, ready]);

  const sampleRows = signals.filter((s) => targetIds.has(s.transcriptId)).slice(0, 4).map((s) => ({
    transcript_id: s.transcriptId,
    item_type: s.type,
    rank: s.rank,
    category: s.category,
    advisor_quote: s.quote,
    timestamp: s.timestamp,
    evidence_strength: s.evidence,
    rationale: s.rationale,
  }));

  let preview = "";
  if (fmt === "jsonl") preview = sampleRows.map((r) => JSON.stringify(r)).join("\n");
  else if (fmt === "json") preview = JSON.stringify(sampleRows, null, 2);
  else
    preview = [
      "transcript_id,item_type,rank,category,advisor_quote,timestamp,evidence_strength,rationale",
      ...sampleRows.map((r) =>
        Object.values(r)
          .map((v) => `"${String(v).replace(/"/g, '""')}"`)
          .join(","),
      ),
    ].join("\n");

  const totalRows = target.reduce((a, t) => a + t.drivers + t.blockers, 0);

  return (
    <>
      <TopBar
        title="Exports"
        subtitle="Agent 5 final schema only · earlier agents stay internal"
      />
      <div className="grid-2 grid-2--asym">
        <Section eyebrow="Configure" title="Export the public final schema">
          <Field label="Scope">
            <div className="seg seg--wide">
              {(
                [
                  ["all", "All completed transcripts"],
                  ["one", "Single transcript"],
                ] as const
              ).map(([k, l]) => (
                <button
                  key={k}
                  type="button"
                  className={"seg__opt " + (scope === k ? "seg__opt--on" : "")}
                  onClick={() => setScope(k)}
                >
                  {l}
                </button>
              ))}
            </div>
          </Field>
          {scope === "one" && (
            <Field label="Transcript">
              <select
                className="select"
                value={pickId}
                onChange={(e) => setPickId(e.target.value)}
              >
                {ready.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} — {t.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Format">
            <div className="seg">
              {(["csv", "json", "jsonl"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  className={"seg__opt " + (fmt === f ? "seg__opt--on" : "")}
                  onClick={() => setFmt(f)}
                >
                  .{f}
                </button>
              ))}
            </div>
          </Field>

          <div className="schema">
            <div className="eyebrow">Included fields</div>
            <ul className="schema__list">
              {[
                "transcript_id",
                "item_type",
                "rank",
                "category",
                "advisor_quote",
                "timestamp",
                "evidence_strength",
                "rationale",
              ].map((f) => (
                <li key={f}>
                  <span className="mono">{f}</span>
                </li>
              ))}
            </ul>
            <div className="schema__note small slate">
              Earlier-agent metadata (segment scores, intermediate ranks, prompts) is
              intentionally excluded.
            </div>
          </div>

          <div className="export-summary">
            <div>
              <div className="eyebrow">Ready</div>
              <div className="export-summary__big mono">
                {target.length}
                <span className="slate"> transcripts</span>
              </div>
              <div className="small slate">
                {totalRows} signal rows ·{" "}
                {target.reduce((a, t) => a + t.cost, 0).toFixed(4)} USD compute incurred
              </div>
            </div>
            <Btn>Download.{fmt}</Btn>
          </div>
        </Section>

        <Section eyebrow="Preview · first 4 rows" title="What downstream sees">
          <pre className="code mono">{preview}</pre>
        </Section>
      </div>
    </>
  );
}
