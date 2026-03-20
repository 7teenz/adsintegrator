"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { setAuth, type User } from "@/lib/auth";

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email address.");

  useEffect(() => {
    async function verify() {
      const token = searchParams.get("token");
      if (!token) {
        setStatus("error");
        setMessage("Missing verification token.");
        return;
      }

      try {
        const data = await apiFetch<{ verified: boolean; user: User }>(`/auth/verify-email?token=${encodeURIComponent(token)}`, {
          method: "GET",
          noAuth: true,
        });
        setAuth(data.user);
        setStatus("success");
        setMessage("Email verified. Redirecting to your dashboard.");
        setTimeout(() => {
          router.replace("/dashboard");
          router.refresh();
        }, 1000);
      } catch (error) {
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "Verification failed.");
      }
    }

    void verify();
  }, [router, searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">
          {status === "success" ? "Email verified" : status === "error" ? "Verification failed" : "Verifying email"}
        </h1>
        <p className="mt-3 text-sm text-slate-600">{message}</p>
      </div>
    </main>
  );
}
