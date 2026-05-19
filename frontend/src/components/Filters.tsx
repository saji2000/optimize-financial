export function Filters() {
  return (
    <div className="filters">
      <input type="search" placeholder="Filter signals" aria-label="Filter signals" />
      <select aria-label="Signal type">
        <option value="">All types</option>
        <option value="driver">Drivers</option>
        <option value="blocker">Blockers</option>
      </select>
    </div>
  );
}

