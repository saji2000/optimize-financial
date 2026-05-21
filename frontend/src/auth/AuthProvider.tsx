import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import {
  AUTH_SESSION_STORAGE_KEY,
  getCurrentUser,
  login as loginRequest,
} from "../api/client";

export interface AuthUser {
  username: string;
  name: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const session = readStoredSession();
    if (!session) {
      setLoading(false);
      return;
    }

    getCurrentUser(session.accessToken)
      .then((currentUser) => {
        if (alive) setUser(currentUser);
      })
      .catch(() => {
        if (!alive) return;
        clearStoredSession();
        setUser(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      clearStoredSession();
      setUser(null);
    }
    window.addEventListener("optimize-auth-unauthorized", handleUnauthorized);
    return () => window.removeEventListener("optimize-auth-unauthorized", handleUnauthorized);
  }, []);

  async function signIn(username: string, password: string) {
    const session = await loginRequest(username, password);
    const storedSession = { accessToken: session.access_token, user: session.user };
    writeStoredSession(storedSession);
    setUser(storedSession.user);
  }

  function signOut() {
    clearStoredSession();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

function readStoredSession(): { accessToken: string; user: AuthUser } | null {
  const raw = window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { accessToken?: unknown; user?: unknown };
    if (
      typeof parsed.accessToken === "string" &&
      parsed.user &&
      typeof parsed.user === "object" &&
      "username" in parsed.user &&
      "name" in parsed.user &&
      "role" in parsed.user
    ) {
      return parsed as { accessToken: string; user: AuthUser };
    }
  } catch {
    // Ignore malformed local auth state.
  }
  return null;
}

function writeStoredSession(session: { accessToken: string; user: AuthUser }) {
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

function clearStoredSession() {
  window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
}
