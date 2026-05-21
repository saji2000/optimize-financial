import { NavLink, useNavigate } from "react-router-dom";
import { Wordmark } from "./primitives";
import { useAuth } from "../auth/AuthProvider";

const items = [
  { k: "/dashboard", label: "Dashboard", icon: "▦" },
  { k: "/transcripts", label: "Transcripts", icon: "≡" },
  { k: "/review", label: "Signal review", icon: "◔" },
  { k: "/pipeline", label: "Pipeline runs", icon: "⌾" },
  { k: "/upload", label: "Upload", icon: "↥" },
  { k: "/analytics", label: "Cost & usage", icon: "◐" },
  { k: "/exports", label: "Exports", icon: "↗" },
];

export function Sidebar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    signOut();
    navigate("/login");
  }

  const initials = user?.name
    ? user.name.split(" ").map((s) => s[0]).join("")
    : "—";

  return (
    <aside className="sidebar">
      <div className="sidebar__head">
        <Wordmark />
      </div>
      <nav className="sidebar__nav">
        {items.map((it) => (
          <NavLink
            key={it.k}
            to={it.k}
            className={({ isActive }) => "navbtn " + (isActive ? "navbtn--active" : "")}
            style={{ textDecoration: "none" }}
          >
            <span className="navbtn__icon">{it.icon}</span>
            <span>{it.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar__foot">
        <div className="user">
          <div className="user__avatar">{initials}</div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="user__name">{user?.name ?? "Signed out"}</div>
            <div className="user__role">{user?.role ?? ""}</div>
          </div>
          <button className="iconbtn" title="Sign out" onClick={handleLogout}>
            ⏏
          </button>
        </div>
      </div>
    </aside>
  );
}
