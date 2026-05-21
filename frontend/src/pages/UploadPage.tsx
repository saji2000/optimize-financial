import { useState, DragEvent, ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { DATA_MODE, getTranscript, uploadTranscript } from "../api/client";
import { Section, StatusPill, TopBar } from "../components/primitives";
import { useData } from "../data/DataProvider";

interface UploadFile {
  id: string;
  name: string;
  size: number;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  error?: string;
}

export function UploadPage() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [drag, setDrag] = useState(false);
  const navigate = useNavigate();
  const { refresh } = useData();

  function add(list: FileList) {
    Array.from(list).forEach((file, i) => {
      const localId = "upload-" + Date.now() + "-" + i;
      const row: UploadFile = {
        id: localId,
        name: file.name.replace(/\.txt$/i, ""),
        size: file.size,
        status: "queued",
        progress: 0,
      };
      setFiles((arr) => [...arr, row]);
      if (DATA_MODE === "mock") {
        simulateUpload(localId);
      } else {
        void sendToBackend(localId, file);
      }
    });
  }

  function simulateUpload(id: string) {
    setTimeout(() => bump(id, "running", 10), 600);
    [22, 38, 55, 68, 80, 92, 100].forEach((p, idx) => {
      setTimeout(
        () => bump(id, p === 100 ? "completed" : "running", p),
        900 + idx * 500,
      );
    });
  }

  async function sendToBackend(localId: string, file: File) {
    try {
      const created = await uploadTranscript(file);
      setFiles((arr) =>
        arr.map((item) =>
          item.id === localId
            ? { ...item, id: created.id, status: created.status === "queued" ? "queued" : "running", progress: 8 }
            : item,
        ),
      );
      await refresh();
      pollTranscript(created.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setFiles((arr) =>
        arr.map((item) =>
          item.id === localId ? { ...item, status: "failed", progress: 100, error: message } : item,
        ),
      );
    }
  }

  function pollTranscript(id: string) {
    let progress = 18;
    const tick = async () => {
      try {
        const detail = await getTranscript(id);
        const status = detail.status === "completed" || detail.status === "failed" ? detail.status : "running";
        progress = status === "completed" || status === "failed" ? 100 : Math.min(progress + 12, 88);
        bump(id, status, progress);
        await refresh();
        if (status !== "completed" && status !== "failed") {
          setTimeout(tick, 2500);
        }
      } catch {
        progress = Math.min(progress + 8, 72);
        bump(id, "running", progress);
        setTimeout(tick, 3000);
      }
    };
    setTimeout(tick, 1200);
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
            - we kick off Agent 1 to Agent 5 automatically
          </div>
          <div className="drop__rules small slate">
            <span>UTF-8 - plain text</span>
            <span>2 MB / file recommended</span>
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
                      <span className="slate small">- {(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                    {f.error && <div className="small slate">{f.error}</div>}
                  </td>
                  <td><StatusPill status={f.status} /></td>
                  <td>
                    <div className="prog">
                      <div className="prog__fill" style={{ width: f.progress + "%" }} />
                    </div>
                  </td>
                  <td>
                    {f.status === "completed" ? (
                      <button className="link" onClick={() => navigate(`/transcripts/${f.id}`)}>
                        open transcript -&gt;
                      </button>
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
