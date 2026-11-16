// AuthContext.jsx - Handles user login, JWT tokens in localStorage and auth state

import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginUser, registerUser, getCurrentUser } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Check if token exists in localStorage on startup
  useEffect(() => {
    async function initAuth() {
      const storedToken = localStorage.getItem('token');
      // console.log("stored token on load:", storedToken)
      if (storedToken) {
        try {
          const profile = await getCurrentUser();
          // console.log("got profile:", profile)
          setUser(profile);
          setToken(storedToken);
        } catch (err) {
          console.warn('Session expired or invalid:', err.message);
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    }

    initAuth();
  }, []);

  const login = async (email, password) => {
    // console.log("logging in:", email)
    const data = await loginUser(email, password);
    const accessToken = data.access_token;
    // console.log("got token:", accessToken)
    localStorage.setItem('token', accessToken);
    setToken(accessToken);
    setUser(data.user);
    // TODO: fix this re-render later
    return data.user;
  };

  const register = async (email, password, organizationName) => {
    const data = await registerUser(email, password, organizationName);
    const accessToken = data.access_token;
    localStorage.setItem('token', accessToken);
    setToken(accessToken);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: Boolean(token && user),
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
