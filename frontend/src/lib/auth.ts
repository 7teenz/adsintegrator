"use client";

const USER_KEY = "maa_user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  email_verified: boolean;
}

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

export function getUser(): User | null {
  if (!hasWindow()) return null;
  const raw = sessionStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function setAuth(user: User): void {
  if (!hasWindow()) return;
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  if (!hasWindow()) return;
  sessionStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getUser());
}
