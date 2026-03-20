"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FileBarChart, Settings, LogOut } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { clearAuth, getUser } from "@/lib/auth";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Audit Report", icon: FileBarChart, href: "/dashboard/audits" },
  { label: "Settings", icon: Settings, href: "/dashboard/settings" },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const user = getUser();

  const handleLogout = async () => {
    try {
      await apiFetch<{ message: string }>("/auth/logout", { method: "POST", noAuth: true });
    } finally {
      clearAuth();
      router.push("/");
      router.refresh();
    }
  };

  return (
    <aside className="hidden w-72 flex-col border-r border-slate-200 bg-white/80 px-4 py-6 backdrop-blur lg:flex">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-lg font-bold tracking-tight text-slate-900">Meta Audit</p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">local MVP</span>
        </div>
        <p className="mt-2 text-xs text-slate-500">Upload an export, audit the account, and review the highest-impact fixes.</p>
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
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Access</p>
        <p className="mt-2 text-sm font-semibold text-slate-900">Included in this MVP</p>
        <p className="mt-2 text-xs text-slate-500">Advanced billing is not enabled in this build. The focus is the upload, audit, and review loop.</p>
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
    </aside>
  );
}
