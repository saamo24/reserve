'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import axios from 'axios';

const AUTH_STORAGE_KEY = 'access_token';
const REFRESH_STORAGE_KEY = 'refresh_token';
const getBaseUrl = (): string => {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return 'http://localhost:8000';
};

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? localStorage.getItem(AUTH_STORAGE_KEY) : null;
    setToken(stored);
    setHydrated(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await axios.post<{ access_token: string; refresh_token: string }>(
      `${getBaseUrl()}/auth/login`,
      { email, password },
      { headers: { 'Content-Type': 'application/json' } }
    );
    localStorage.setItem(AUTH_STORAGE_KEY, data.access_token);
    localStorage.setItem(REFRESH_STORAGE_KEY, data.refresh_token);
    setToken(data.access_token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(REFRESH_STORAGE_KEY);
    setToken(null);
  }, []);

  const value: AuthContextValue = {
    isAuthenticated: hydrated && !!token,
    isLoading: !hydrated,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
