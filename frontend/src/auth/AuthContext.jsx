import React from "react";
import { clearToken, getToken, setToken } from "../api/storage.js";
import * as api from "../api/client.js";

const AuthContext = React.createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const token = getToken();

  const refresh = React.useCallback(async () => {
    const t = getToken();
    if (!t) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await api.me();
      setUser(res?.data || null);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh, token]);

  const login = React.useCallback(async (username, password) => {
    const res = await api.login(username, password);
    const t = res?.data?.token;
    if (!t) throw new Error("Token missing in response");
    setToken(t);
    setUser({ username: res?.data?.username, is_admin: !!res?.data?.is_admin });
  }, []);

  const logout = React.useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

