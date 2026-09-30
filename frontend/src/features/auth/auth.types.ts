/**
 * Auth types. Authentication itself is handled by Supabase Auth (integrated by M1/backend).
 * This frontend only needs a thin session shape to drive UI state and to source the
 * bearer token attached to outgoing API requests.
 */

export interface AuthUser {
  id: string;
  email: string;
}

export interface AuthSession {
  user: AuthUser;
  accessToken: string;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface LoginFormValues {
  email: string;
  password: string;
}
