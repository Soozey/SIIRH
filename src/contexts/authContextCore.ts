import { createContext } from "react";

import type { AuthSession } from "../api";

export type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthSession>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<AuthSession>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
