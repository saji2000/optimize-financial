import { EvidenceQuote } from "./EvidenceQuote";
import { StatusBadge } from "./StatusBadge";

export function SignalTable() {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Type</th>
          <th>Category</th>
          <th>Summary</th>
          <th>Evidence</th>
          <th>Strength</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Driver</td>
          <td>Practice fit</td>
          <td>Advisor values clean client-facing explanations.</td>
          <td>
            <EvidenceQuote quote="The story has to be easy to explain to clients." />
          </td>
          <td>
            <StatusBadge status="explicit" />
          </td>
        </tr>
      </tbody>
    </table>
  );
}
