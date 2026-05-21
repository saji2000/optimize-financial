import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Btn, Money, ReviewPill, StatusPill, TopBar } from "../components/primitives";
import { useTranscripts } from "../data/DataProvider";

export function LibraryPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [review, setReview] = useState("all");
  const [sort, setSort] = useState("date");
  const navigate = useNavigate();
  const transcripts = useTranscripts();

  const rows = useMemo(() => {
    let r = transcripts.slice();
    if (q) {
      const lq = q.toLowerCase();
      r = r.filter(
        (t) =>
          t.name.toLowerCase().includes(lq) ||
          t.id.toLowerCase().includes(lq) ||
          t.client.toLowerCase().includes(lq),
      );
    }
    if (status !== "all") r = r.filter((t) => t.status === status);
    if (review !== "all") r = r.filter((t) => t.reviewState === review);
    r.sort((a, b) => {
      if (sort === "cost") return b.cost - a.cost;
      if (sort === "drivers") return b.drivers - a.drivers;
      return b.uploaded.localeCompare(a.uploaded);
    });
    return r;
  }, [q, status, review, sort]);

  return (
    <>
      <TopBar
        title="Transcripts"
        subtitle={`${transcripts.length} files · ${transcripts.filter((t) => t.status === "completed").length} ready for review`}
        right={<Btn onClick={() => navigate("/upload")}>Upload .txt →</Btn>}
      />

      <div className="toolbar">
        <input
          className="input input--search"
          placeholder="Search by id, file, or client…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="toolbar__group">
          <label className="lbl">Status</label>
          <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">all</option>
            <option value="completed">completed</option>
            <option value="running">running</option>
            <option value="queued">queued</option>
            <option value="failed">failed</option>
          </select>
        </div>
        <div className="toolbar__group">
          <label className="lbl">Review</label>
          <select className="select" value={review} onChange={(e) => setReview(e.target.value)}>
            <option value="all">all</option>
            <option value="pending">pending</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
        </div>
        <div className="toolbar__group">
          <label className="lbl">Sort</label>
          <select className="select" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="date">most recent</option>
            <option value="cost">estimated cost (high→low)</option>
            <option value="drivers">most drivers</option>
          </select>
        </div>
      </div>

      <div className="card">
        <table className="t t--lib">
          <thead>
            <tr>
              <th style={{ width: "30%" }}>Transcript</th>
              <th>Status</th>
              <th>Review</th>
              <th className="num">Drivers</th>
              <th className="num">Blockers</th>
              <th className="num">Estimated LLM cost</th>
              <th>Export</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr
                key={t.id}
                onClick={() => navigate(`/transcripts/${t.id}`)}
                className="trow"
              >
                <td>
                  <div className="mono small slate">{t.id} · {t.uploaded}</div>
                  <div className="strong">{t.name}</div>
                  <div className="small slate">{t.advisor} · {t.client}</div>
                </td>
                <td><StatusPill status={t.status} /></td>
                <td><ReviewPill state={t.reviewState} /></td>
                <td className="num mono">{t.drivers || "—"}</td>
                <td className="num mono">{t.blockers || "—"}</td>
                <td className="num">
                  <Money value={t.cost} />
                  {t.calls === 0 && <div className="small slate">No usage recorded yet</div>}
                </td>
                <td>
                  {t.exportReady ? (
                    <span className="tag tag--ink">ready</span>
                  ) : (
                    <span className="tag tag--ghost">—</span>
                  )}
                </td>
                <td className="num">
                  <span className="link">open →</span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">
                  No transcripts match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
