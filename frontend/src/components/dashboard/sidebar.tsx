"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FileBarChart, Settings, LogOut, Sparkles } from "lucide-react";

import { clearAuth, getUser } from "@/lib/auth";
import { usePlan } from "@/lib/plan";
import { UpgradeCta } from "@/components/billing/upgrade-cta";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Audit Report", icon: FileBarChart, href: "/dashboard/audits" },
  { label: "Settings", icon: Settings, href: "/dashboard/settings" },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const user = getUser();
  const { plan, isPremium } = usePlan();

  const handleLogout = () => {
    clearAuth();
    router.push("/");
  };

  return (
    <aside className="hidden w-72 flex-col border-r border-slate-200 bg-white/80 px-4 py-6 backdrop-blur lg:flex">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-lg font-bold tracking-tight text-slate-900">Meta Audit</p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">v0.5</span>
        </div>
        <p className="mt-2 text-xs text-slate-500">Deterministic ad-account intelligence</p>
      </div>

      <nav className="mt-6 space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Current Plan</p>
          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${isPremium ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
            {plan}
          </span>
        </div>
        {!isPremium ? (
          <div className="mt-3">
            <UpgradeCta compact title="Unlock Full Report" body="See full findings, advanced trend blocks, and long-range history." />
          </div>
        ) : (
          <p className="mt-3 text-sm text-emerald-700">Premium insights unlocked.</p>
        )}
      </div>

      <div className="mt-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="truncate text-sm text-slate-700">{user?.email || "Not signed in"}</p>
        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-rose-600"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>

      {!isPremium ? (
        <Link href="/dashboard/settings" className="mt-4 inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
          <Sparkles className="h-4 w-4" />
          Upgrade
        </Link>
      ) : null}
    </aside>
  );
}
