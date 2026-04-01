import Link from "next/link";

import { Hero } from "@/components/landing/hero";

const howItWorks = [
  {
    title: "1. Export from Ads Manager",
    body: "Upload a CSV or XLSX export from Meta Ads Manager. No OAuth setup is required to get started.",
  },
  {
    title: "2. Generate the audit",
    body: "The platform scores account health, ranks wasted spend signals, and builds a focused report.",
  },
  {
    title: "3. Prioritize fixes",
    body: "Review the most expensive issues first and move from diagnosis to action without manual spreadsheet work.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_32%),linear-gradient(180deg,_#ffffff,_#f8fafc)]">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="text-lg font-bold text-slate-900">Meta Ads Audit</span>
        <div className="flex items-center gap-5 text-sm font-medium text-slate-600">
          <Link href="#how-it-works" className="hover:text-slate-900">
            How It Works
          </Link>
          <Link href="#trust" className="hover:text-slate-900">
            Trust
          </Link>
          <Link href="/login" className="text-brand-600 hover:text-brand-700">
            Sign In
          </Link>
        </div>
      </nav>

      <Hero />

      <section id="how-it-works" className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">How It Works</p>
          <h2 className="mt-2 text-3xl font-semibold text-slate-900">A faster path from export to action</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {howItWorks.map((item) => (
            <article key={item.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="trust" className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Trust</p>
          <h2 className="mt-2 text-3xl font-semibold text-slate-900">Built for a credible audit workflow</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {[
            "Uploaded reports stay inside your project environment and are not shared with third parties.",
            "You can remove imported data and delete the account at any time from Settings.",
            "No live billing is required to run a full audit.",
          ].map((item) => (
            <article key={item} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm leading-6 text-slate-600">{item}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-200 px-6 py-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Meta Ads Audit</p>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-slate-900">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-slate-900">
              Terms
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
