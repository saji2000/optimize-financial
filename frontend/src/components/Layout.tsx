import { BarChart3, FileText, GitBranch, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Advisor Signal Extraction</div>
        <nav>
          <NavLink to="/">
            <BarChart3 size={18} />
            Signals
          </NavLink>
          <NavLink to="/transcripts">
            <FileText size={18} />
            Transcripts
          </NavLink>
          <NavLink to="/review">
            <Inbox size={18} />
            Review
          </NavLink>
          <NavLink to="/pipeline-runs">
            <GitBranch size={18} />
            Runs
          </NavLink>
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
