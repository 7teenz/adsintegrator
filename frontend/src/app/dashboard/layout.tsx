"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { Sidebar } from "@/components/dashboard/sidebar";
import { apiFetch } from "@/lib/api";
import { getToken, setAuth, type User } from "@/lib/auth";
import { PlanProvider } from "@/lib/plan";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = useState<"loading" | "ready">("loading");

  useEffect(() => {
    async function validateSession() {
      const token = getToken();
      if (!token) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }

      try {
        const user = await apiFetch<User>("/auth/me");
        setAuth(token, user);
        setStatus("ready");
      } catch {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      }
    }

    void validateSession();
  }, [pathname, router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-900 border-t-transparent" />
      </div>
    );
  }

  return (
    <PlanProvider>
      <div className="min-h-screen bg-app">
        <div className="mx-auto flex w-full max-w-[1500px]">
          <Sidebar />
          <main className="min-h-screen flex-1 px-4 py-6 sm:px-6 lg:px-10">
            <div className="mb-5 flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm backdrop-blur lg:hidden">
              <p className="text-sm font-semibold text-slate-900">Meta Audit</p>
              <Link href="/dashboard/settings" className="text-xs font-semibold text-slate-600">
                Plan Settings
              </Link>
            </div>
            {children}
          </main>
        </div>
      </div>
    </PlanProvider>
  );
}
