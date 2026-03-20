"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { setAuth } from "@/lib/auth";

interface AuthCardProps {
  mode: "login" | "register";
  nextHref?: string;
}

interface AuthResponse {
  user: {
    id: string;
    email: string;
    full_name: string | null;
    is_active: boolean;
    email_verified: boolean;
  };
}

export function AuthCard({ mode, nextHref = "/dashboard" }: AuthCardProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const isLogin = mode === "login";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const payload = isLogin
        ? { email, password }
        : { email, password, full_name: fullName || undefined };

      const data = await apiFetch<AuthResponse | { message: string }>(isLogin ? "/auth/login" : "/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
        noAuth: true,
      });

      if (isLogin) {
        setAuth((data as AuthResponse).user);
        router.push(nextHref);
        router.refresh();
      } else {
        setSuccess((data as { message: string }).message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  const alternateHref = isLogin ? "/register" : "/login";

  return (
    <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.35)]">
      <div className="mb-8">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-600">Meta Ads Audit</p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-900">
          {isLogin ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          {isLogin
            ? "Sign in to connect your Meta Ads account and choose the ad account to audit."
            : "Create an account to start your Meta OAuth connection flow."}
        </p>
      </div>

      {error ? (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {success}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        {!isLogin ? (
          <label className="block text-sm text-slate-600">
            Full name
            <input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand-500"
              placeholder="Jane Doe"
            />
          </label>
        ) : null}

        <label className="block text-sm text-slate-600">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand-500"
            placeholder="you@company.com"
          />
        </label>

        <label className="block text-sm text-slate-600">
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-brand-500"
            placeholder="At least 8 characters"
          />
        </label>

        <Button type="submit" className="w-full" size="lg" disabled={loading}>
          {loading ? "Please wait..." : isLogin ? "Sign in" : "Create account"}
        </Button>
      </form>

      <p className="mt-6 text-sm text-slate-500">
        {isLogin ? "Need an account?" : "Already have an account?"}{" "}
        <Link href={alternateHref} className="font-medium text-brand-600">
          {isLogin ? "Register" : "Sign in"}
        </Link>
      </p>
      {isLogin ? (
        <p className="mt-2 text-sm text-slate-500">
          <Link href="/forgot-password" className="font-medium text-brand-600">
            Forgot password?
          </Link>
        </p>
      ) : null}
    </div>
  );
}
