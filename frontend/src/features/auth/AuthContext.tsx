import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { supabase, isSupabaseConfigured } from "@/lib/supabase";
import type { AuthSession, AuthStatus } from "./auth.types";

interface AuthContextValue {
  status: AuthStatus;
  session: AuthSession | null;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toAuthSession(supabaseSession: {
  access_token: string;
  user: { id: string; email?: string | null };
} | null): AuthSession | null {
  if (!supabaseSession) return null;
  return {
    accessToken: supabaseSession.access_token,
    user: {
      id: supabaseSession.user.id,
      email: supabaseSession.user.email ?? "",
    },
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setStatus("unauthenticated");
      return;
    }

    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const nextSession = toAuthSession(data.session);
      setSession(nextSession);
      setStatus(nextSession ? "authenticated" : "unauthenticated");
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      const nextSession = toAuthSession(newSession);
      setSession(nextSession);
      setStatus(nextSession ? "authenticated" : "unauthenticated");
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      session,
      signIn: async (email: string, password: string) => {
        if (!isSupabaseConfigured) {
          return { error: "Authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY." };
        }
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        return { error: error?.message ?? null };
      },
      signOut: async () => {
        if (!isSupabaseConfigured) return;
        await supabase.auth.signOut();
      },
    }),
    [status, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
