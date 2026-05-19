import { TranscriptTable } from "../components/TranscriptTable";

export function TranscriptListPage() {
  return (
    <section className="page">
      <div className="page-header">
        <h1>Transcripts</h1>
        <p>Uploaded transcripts and processing state.</p>
      </div>
      <TranscriptTable />
    </section>
  );
}

