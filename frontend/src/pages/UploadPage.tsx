import { useState, DragEvent, ChangeEvent } from "react";
import { Section, StatusPill, TopBar } from "../components/primitives";

interface UploadFile {
  id: string;
  name: string;
  size: number;
  status: "queued" | "running" | "completed";
  progress: number;
}

export function UploadPage() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [drag, setDrag] = useState(false);

  function add(list: FileList) {
    const next: UploadFile[] = Array.from(list).map((f, i) => ({
      id: "TR-" + (2042 + files.length + i),
      name: f.name.replace(/\.txt$/i, ""),
      size: f.size,
      status: "queued",
      progress: 0,
    }));
    setFiles((arr) => [...arr, ...next]);
    next.forEach((file) => {
      setTimeout(() => bump(file.id, "running", 10), 600);
      [22, 38, 55, 68, 80, 92, 100].forEach((p, idx) => {
        setTimeout(
          () => bump(file.id, p === 100 ? "completed" : "running", p),
          900 + idx * 500,
        );
      });
    });
  }

  function bump(id: string, status: UploadFile["status"], progress: number) {
    setFiles((arr) =>
      arr.map((f) => (f.id === id ? { ...f, status, progress } : f)),
    );
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files) add(e.dataTransfer.files);
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files) add(e.target.files);
  }

  return (
    <>
      <TopBar
        title="Upload transcripts"
        subtitle="Drop .txt files to start the 5-step pipeline"
      />
      <div
        className={"drop " + (drag ? "drop--on" : "")}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <div className="drop__inner">
          <div className="drop__icon">↥</div>
          <div className="drop__title">Drop .txt transcripts here</div>
          <div className="drop__sub">
            or{" "}
            <label className="link">
              <input
                type="file"
                accept=".txt"
                multiple
                style={{ display: "none" }}
                onChange={onPick}
              />
              browse files
            </label>{" "}
            · we kick off Agent 1 → Agent 5 automatically
          </div>
          <div className="drop__rules small slate">
            <span>UTF-8 · plain text</span>
            <span>≤ 2 MB / file</span>
            <span>processed in order</span>
          </div>
        </div>
      </div>

      {files.length > 0 && (
        <Section eyebrow="Session" title="Files in this upload">
          <table className="t">
            <thead>
              <tr>
                <th>File</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id}>
                  <td>
                    <div className="mono small slate">{f.id}</div>
                    <div>
                      {f.name}.txt{" "}
                      <span className="slate small">· {(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                  </td>
                  <td><StatusPill status={f.status} /></td>
                  <td>
                    <div className="prog">
                      <div className="prog__fill" style={{ width: f.progress + "%" }} />
                    </div>
                  </td>
                  <td>
                    {f.status === "completed" ? (
                      <span className="link">open transcript →</span>
                    ) : (
                      <span className="slate small">{f.progress}%</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
    </>
  );
}
