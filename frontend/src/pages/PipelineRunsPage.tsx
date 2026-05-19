import { StatusBadge } from "../components/StatusBadge";

export function PipelineRunsPage() {
  return (
    <section className="page">
      <div className="page-header">
        <h1>Pipeline runs</h1>
        <p>Worker execution status for transcript processing.</p>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Run</th>
            <th>Transcript</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>run-001</td>
            <td>call-001</td>
            <td>
              <StatusBadge status="queued" />
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

