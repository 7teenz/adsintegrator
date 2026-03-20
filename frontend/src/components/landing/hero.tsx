"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function Hero() {
  const router = useRouter();

  return (
    <section className="px-6 py-20 sm:py-24">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <div className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sm text-sky-700">
            Local MVP Meta audit
          </div>
          <h1 className="mt-6 max-w-4xl text-5xl font-bold tracking-tight text-slate-900 sm:text-6xl">
            Find wasted Meta Ads spend and the fixes most likely to improve results.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
            Upload your Ads Manager export. Get a prioritized audit in minutes, with executive takeaways, the biggest leaks, and the next actions worth taking.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Button size="lg" onClick={() => router.push("/register")}>
              Start local audit
            </Button>
            <Button size="lg" variant="secondary" onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}>
              How It Works
            </Button>
          </div>
        </div>

        <div className="grid gap-4">
          {[
            { label: "Executive Verdict", desc: "Lead with the account readout, not a wall of metrics." },
            { label: "Wasted Spend", desc: "Pinpoint where budget is leaking before it compounds across the month." },
            { label: "Fix Queue", desc: "Get a practical order of operations instead of another vanity dashboard." },
          ].map((item) => (
            <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900">{item.label}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
