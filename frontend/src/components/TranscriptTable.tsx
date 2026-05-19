import { StatusBadge } from "./StatusBadge";

export function TranscriptTable() {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Transcript</th>
          <th>Advisor</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>call-001</td>
          <td>Sample Advisor</td>
          <td>
            <StatusBadge status="queued" />
          </td>
        </tr>
      </tbody>
    </table>
  );
}

