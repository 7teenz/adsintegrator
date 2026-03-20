"use client";

import { useEffect, useState } from "react";

import { AdAccountSelector } from "@/components/dashboard/ad-account-selector";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface MetaConnection {
  id: string;
  meta_user_id: string;
  meta_user_name: string | null;
  token_expires_at: string | null;
  has_selected_account: boolean;
}

interface ConnectionStatus {
  connected: boolean;
  connection: MetaConnection | null;
}

export function MetaConnect() {
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [showAccounts, setShowAccounts] = useState(false);
  const [error, setError] = useState("");

  async function fetchStatus() {
    try {
      const data = await apiFetch<ConnectionStatus>("/meta/connection");
      setStatus(data);
      setShowAccounts(Boolean(data.connected && !data.connection?.has_selected_account));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check Meta connection status")
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchStatus();
  }, []);

  async function handleConnect() {
    setConnecting(true);
    setError("");

    try {
      const data = await apiFetch<{ url: string }>("/meta/auth-url");
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start Meta OAuth")
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    try {
      await apiFetch<void>("/meta/connection", { method: "DELETE" });
      setStatus({ connected: false, connection: null });
      setShowAccounts(false);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect Meta account")
    }
  }

  function handleSelected() {
    setShowAccounts(false);
    void fetchStatus();
  }

  if (loading) {
    return (
      <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6">
        <div className="h-5 w-48 animate-pulse rounded-full bg-slate-200" />
      </div>
    );
  }

  if (status?.connected && status.connection) {
    return (
      <section className="space-y-4 rounded-[1.5rem] border border-emerald-200 bg-white p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-600">Meta connected</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-900">
              {status.connection.meta_user_name || status.connection.meta_user_id}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {status.connection.has_selected_account
                ? "Your Meta connection is ready and an ad account is selected."
                : "Your Meta user is connected. Choose which ad account we should use."}
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setShowAccounts((value) => !value)}>
              {showAccounts ? "Hide accounts" : "Choose account"}
            </Button>
            <Button variant="ghost" onClick={handleDisconnect}>Disconnect</Button>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        {showAccounts || !status.connection.has_selected_account ? (
          <AdAccountSelector onSelect={handleSelected} />
        ) : null}
      </section>
    );
  }

  return (
    <section className="rounded-[1.5rem] border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-brand-600">Meta OAuth</p>
      <h2 className="mt-3 text-2xl font-semibold text-slate-900">Connect your Meta Ads account</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-500">
        We will redirect you to Meta for consent, store the returned access token encrypted at rest, fetch the ad accounts available to your Meta user, and let you select the account to audit.
      </p>
      {error ? (
        <div className="mx-auto mt-4 max-w-xl rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      <Button className="mt-6" size="lg" onClick={handleConnect} disabled={connecting}>
        {connecting ? "Redirecting to Meta..." : "Connect Meta account"}
      </Button>
    </section>
  );
}
