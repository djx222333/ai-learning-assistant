// AuthContext — 全局认证状态管理
// 提供: token / currentUser / login / logout / register / isAuthenticated / loading

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import http from "../api/http";

const TOKEN_KEY = "ai_learning_token";
const USER_KEY = "ai_learning_user";

export interface AuthUser {
  id: string;
  username: string;
  email?: string;
  is_active: boolean;
  created_at: string;
}

interface AuthContextType {
  token: string | null;
  user: AuthUser | null;
  loading: boolean;        // 初始化中（正在恢复登录态）
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // 页面刷新后：用 token 自动恢复用户信息
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (!savedToken) {
      setLoading(false);
      return;
    }
    http
      .get<AuthUser>("/v1/auth/me")
      .then((resp) => {
        setUser(resp.data);
        localStorage.setItem(USER_KEY, JSON.stringify(resp.data));
      })
      .catch(() => {
        // token 过期或无效
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // 监听全局登出事件（来自 http.ts 的 401 拦截器）
  useEffect(() => {
    const handler = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  // 登录
  const login = useCallback(async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const resp = await http.post<{
      access_token: string;
      token_type: string;
      user: AuthUser;
    }>("/v1/auth/login", formData.toString(), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    const { access_token, user: userData } = resp.data;
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
  }, []);

  // 注册
  const register = useCallback(async (username: string, password: string, email?: string) => {
    await http.post("/v1/auth/register", {
      username,
      password,
      email: email || undefined,
    });
  }, []);

  // 登出
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        loading,
        isAuthenticated: !!token && !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}