"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function MetaCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"processing" | "success" | "error">("processing");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function handleCallback() {
      if (!getToken()) {
        router.replace("/login?next=/dashboard");
        return;
      }

      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const error = searchParams.get("error");

      if (error) {
        setStatus("error");
        setErrorMessage(searchParams.get("error_description") || "Meta authorization was declined.");
        return;
      }

      if (!code || !state) {
        setStatus("error");
        setErrorMessage("Missing OAuth code or state in the Meta callback.");
        return;
      }

      try {
        await apiFetch("/meta/callback", {
          method: "POST",
          body: JSON.stringify({ code, state }),
        });
        setStatus("success");
        setTimeout(() => router.replace("/dashboard"), 1200);
      } catch (err) {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Failed to complete the Meta connection.")
      }
    }

    void handleCallback();
  }, [router, searchParams]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="w-full max-w-lg rounded-[2rem] border border-slate-200 bg-white p-8 text-center shadow-[0_24px_80px_-32px_rgba(15,23,42,0.28)]">
        {status === "processing" ? (
          <>
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
            <h1 className="mt-5 text-2xl font-semibold text-slate-900">Connecting Meta account</h1>
            <p className="mt-2 text-sm text-slate-500">Validating the callback, exchanging the OAuth code, and fetching available ad accounts.</p>
          </>
        ) : null}

        {status === "success" ? (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">OK</div>
            <h1 className="mt-5 text-2xl font-semibold text-slate-900">Meta connected</h1>
            <p className="mt-2 text-sm text-slate-500">Your token is stored securely and we are sending you back to the dashboard.</p>
          </>
        ) : null}

        {status === "error" ? (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-700">X</div>
            <h1 className="mt-5 text-2xl font-semibold text-slate-900">Connection failed</h1>
            <p className="mt-2 text-sm text-slate-500">{errorMessage}</p>
            <button onClick={() => router.replace("/dashboard")} className="mt-5 text-sm font-medium text-brand-600">
              Return to dashboard
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
