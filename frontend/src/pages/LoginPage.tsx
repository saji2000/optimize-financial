import { useEffect, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { Btn, Field, Wordmark } from "../components/primitives";
import { useAuth } from "../auth/AuthProvider";

function Ticker() {
  const lines: [string, string, string][] = [
    ["00:12:04", "TR-2041", "Agent 5 final formatting complete"],
    ["00:11:58", "TR-2041", "Evidence validation 8/8 passed"],
    ["00:11:42", "TR-2041", "Consolidation 5 drivers, 3 blockers"],
    ["00:10:55", "TR-2040", "Approved 6 signals"],
    ["00:09:21", "TR-2036", "Step 3 retry fallback to mid model"],
    ["00:08:02", "TR-2038", "Running segment extraction 64%"],
  ];
  return (
    <div className="ticker">
      {lines.map((line, i) => (
        <div className="ticker__row" key={i}>
          <span className="mono ticker__t">{line[0]}</span>
          <span className="mono ticker__id">{line[1]}</span>
          <span className="ticker__msg">{line[2]}</span>
        </div>
      ))}
    </div>
  );
}

export function LoginPage() {
  const [username, setUsername] = useState("curtis");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) navigate("/dashboard", { replace: true });
  }, [loading, navigate, user]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      showError("Enter your username and password.");
      return;
    }

    setSubmitting(true);
    try {
      await signIn(username.trim(), password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        showError("Invalid username or password.");
      } else {
        showError("Unable to sign in. Check that the backend is running.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function showError(message: string) {
    setError(message);
    setShake(true);
    window.setTimeout(() => setShake(false), 400);
  }

  return (
    <div className="login">
      <div className="login__left">
        <div className="login__brand">
          <Wordmark size={22} />
        </div>

        <form className={"login__card " + (shake ? "shake" : "")} onSubmit={submit}>
          <div className="eyebrow">Internal Review / Agent 5</div>
          <h1 className="login__title">
            Sign in to review
            <br />
            today's transcripts.
          </h1>
          <p className="login__lede">
            Inspect Agent 5 output, verify evidence, and approve final drivers and blockers
            before they are surfaced to business users.
          </p>

          <div className="login__fields">
            <Field label="Username">
              <input
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </Field>
            <Field label="Password">
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </Field>
          </div>

          {error && <div className="login__error">{error}</div>}

          <Btn full type="submit" disabled={submitting || loading}>
            {submitting ? "Signing in..." : "Sign in"}
          </Btn>
        </form>

        <footer className="login__foot">
          <span>v0.4.1 / Agent 5 pipeline</span>
          <span>Internal use only</span>
        </footer>
      </div>

      <div className="login__right" aria-hidden="true">
        <div className="login__plate">
          <div className="login__stamp">
            <div className="eyebrow" style={{ color: "rgba(255,255,255,.55)" }}>
              Pipeline status / live
            </div>
            <div className="login__big">
              8<span style={{ opacity: 0.5 }}>/</span>9
            </div>
            <div className="login__big-sub">transcripts completed today</div>
          </div>
          <div className="login__ticker">
            <Ticker />
          </div>
          <div className="login__legal">2026 / Internal preview build</div>
        </div>
      </div>
    </div>
  );
}
