import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  type AuthSession,
  fetchCurrentSession,
  getStoredSession,
  loginRequest,
  logoutRequest,
  storeSession,
} from "../api";


type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthSession>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);


export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => getStoredSession());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      const stored = getStoredSession();
      if (!stored?.token) {
        if (active) setLoading(false);
        return;
      }

      try {
        const refreshed = await fetchCurrentSession();
        if (!active) return;
        storeSession(refreshed);
        setSession(refreshed);
      } catch {
        if (!active) return;
        storeSession(null);
        setSession(null);
      } finally {
        if (active) setLoading(false);
      }
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      storeSession(null);
      setSession(null);
    };

    window.addEventListener("siirh:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("siirh:unauthorized", handleUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    session,
    loading,
    login: async (username: string, password: string) => {
      const nextSession = await loginRequest(username, password);
      storeSession(nextSession);
      setSession(nextSession);
      return nextSession;
    },
    logout: async () => {
      try {
        if (session?.token) {
          await logoutRequest();
        }
      } catch {
        // Session cleanup still happens locally.
      } finally {
        storeSession(null);
        setSession(null);
      }
    },
  }), [loading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
