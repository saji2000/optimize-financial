import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Btn, Field, Wordmark } from "../components/primitives";
import { useAuth } from "../auth/AuthProvider";

function Ticker() {
  const lines: [string, string, string][] = [
    ["00:12:04", "TR-2041", "Agent 5 · final formatting complete"],
    ["00:11:58", "TR-2041", "Evidence validation · 8/8 passed"],
    ["00:11:42", "TR-2041", "Consolidation · 5 drivers, 3 blockers"],
    ["00:10:55", "TR-2040", "Approved · 6 signals"],
    ["00:09:21", "TR-2036", "Step 3 retry · fallback to haiku"],
    ["00:08:02", "TR-2038", "Running · segment extraction 64%"],
  ];
  return (
    <div className="ticker">
      {lines.map((l, i) => (
        <div className="ticker__row" key={i}>
          <span className="mono ticker__t">{l[0]}</span>
          <span className="mono ticker__id">{l[1]}</span>
          <span className="ticker__msg">{l[2]}</span>
        </div>
      ))}
    </div>
  );
}

export function LoginPage() {
  const [email, setEmail] = useState("morgan@optimize.example");
  const [pw, setPw] = useState("••••••••••");
  const [role, setRole] = useState("Reviewer");
  const [shake, setShake] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setShake(true);
      setTimeout(() => setShake(false), 400);
      return;
    }
    signIn({ name: "Morgan Okafor", role, email });
    navigate("/dashboard");
  }

  function demoLogin() {
    signIn({ name: "Demo User", role: "Reviewer", email: "demo@optimize.example" });
    navigate("/dashboard");
  }

  return (
    <div className="login">
      <div className="login__left">
        <div className="login__brand">
          <Wordmark size={22} />
        </div>

        <form className={"login__card " + (shake ? "shake" : "")} onSubmit={submit}>
          <div className="eyebrow">Internal Review · Agent 5</div>
          <h1 className="login__title">
            Sign in to review
            <br />
            today's transcripts.
          </h1>
          <p className="login__lede">
            Inspect Agent 5 output, verify evidence, and approve final drivers and blockers
            before they're surfaced to advisors.
          </p>

          <div className="login__fields">
            <Field label="Email">
              <input
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
              />
            </Field>
            <Field label="Password">
              <input
                className="input"
                type="password"
                value={pw}
                onChange={(e) => setPw(e.target.value)}
              />
            </Field>
            <Field label="Role (demo)">
              <div className="seg">
                {["Reviewer", "Admin"].map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={"seg__opt " + (role === r ? "seg__opt--on" : "")}
                    onClick={() => setRole(r)}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <Btn full type="submit">
            Sign in
          </Btn>
          <button type="button" className="login__demo" onClick={demoLogin}>
            Continue as demo reviewer →
          </button>
        </form>

        <footer className="login__foot">
          <span>v0.4.1 · Agent 5 pipeline</span>
          <span>SOC 2 Type II · Internal use only</span>
        </footer>
      </div>

      <div className="login__right" aria-hidden="true">
        <div className="login__plate">
          <div className="login__stamp">
            <div className="eyebrow" style={{ color: "rgba(255,255,255,.55)" }}>
              Pipeline status · live
            </div>
            <div className="login__big">
              8<span style={{ opacity: 0.5 }}>/</span>9
            </div>
            <div className="login__big-sub">transcripts completed today</div>
          </div>
          <div className="login__ticker">
            <Ticker />
          </div>
          <div className="login__legal">© 2026 · Internal preview build</div>
        </div>
      </div>
    </div>
  );
}
