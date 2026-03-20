"use client";

import Link from "next/link";
import { useState } from "react";

import { apiFetch } from "@/lib/api";
import { clearAuth, getUser } from "@/lib/auth";

export default function SettingsPage() {
  const user = getUser();
  const [resettingData, setResettingData] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function resetImportedData() {
    if (!window.confirm("Delete imported data, connected ad-account data, sync history, and audit runs for this account?")) {
      return;
    }

    setResettingData(true);
    setError("");
    setMessage("");
    try {
      const response = await apiFetch<{ message: string }>("/auth/data", { method: "DELETE" });
      setMessage(response.message || "Imported data deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete data");
    } finally {
      setResettingData(false);
    }
  }

  async function deleteAccount() {
    if (!window.confirm("Delete your account and all related data? This cannot be undone.")) {
      return;
    }

    setDeletingAccount(true);
    setError("");
    setMessage("");
    try {
      await apiFetch<{ message: string }>("/auth/account", { method: "DELETE" });
      clearAuth();
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete account");
      setDeletingAccount(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Account & Data</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          This local MVP includes the full audit experience in a single plan. Advanced billing is not enabled in this build.
        </p>
      </section>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}
      {message ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Account</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">Profile</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <p>
              Email: <span className="font-semibold text-slate-900">{user?.email || "Unknown"}</span>
            </p>
            <p>
              Name: <span className="font-semibold text-slate-900">{user?.full_name || "Not provided"}</span>
            </p>
            <p>
              Access: <span className="font-semibold text-slate-900">Included in this MVP</span>
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Privacy</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">How this build handles data</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <p>Your uploaded Meta Ads exports stay inside this local project environment for the MVP build.</p>
            <p>You can remove imported data and audits at any time from this page.</p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link href="/privacy" className="font-semibold text-sky-700 hover:text-sky-800">Privacy policy</Link>
              <Link href="/terms" className="font-semibold text-sky-700 hover:text-sky-800">Terms</Link>
            </div>
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Data controls</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-900">Remove imported data</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          This deletes imported campaign data, audit runs, AI summaries, and connected Meta account data for your user.
        </p>
        <button
          type="button"
          onClick={() => void resetImportedData()}
          disabled={resettingData}
          className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
        >
          {resettingData ? "Deleting..." : "Delete imported data"}
        </button>
      </section>

      <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-700">Danger zone</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-900">Delete account</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-700">
          This permanently deletes your account and all related data. Use this only if you want to fully remove your local MVP workspace data for this user.
        </p>
        <button
          type="button"
          onClick={() => void deleteAccount()}
          disabled={deletingAccount}
          className="mt-4 rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-800 disabled:opacity-60"
        >
          {deletingAccount ? "Deleting account..." : "Delete account"}
        </button>
      </section>
    </div>
  );
}
