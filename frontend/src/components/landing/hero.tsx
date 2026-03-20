"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function Hero() {
  const router = useRouter();

  return (
    <section className="flex flex-col items-center justify-center px-6 py-24 text-center">
      <div className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm text-blue-700 mb-6">
        AI-Powered Audit
      </div>

      <h1 className="max-w-3xl text-5xl font-bold tracking-tight text-gray-900 sm:text-6xl">
        Stop wasting money on
        <span className="text-brand-600"> underperforming ads</span>
      </h1>

      <p className="mt-6 max-w-2xl text-lg text-gray-600 leading-relaxed">
        Connect your Meta Ads account and get an instant audit. We calculate
        your Health Score, find wasted spend, and show you exactly what to fix
        — backed by data, not guesswork.
      </p>

      <div className="mt-10 flex gap-4">
        <Button size="lg" onClick={() => router.push("/dashboard")}>
          Start Free Audit
        </Button>
        <Button size="lg" variant="secondary" onClick={() => router.push("#how-it-works")}>
          How It Works
        </Button>
      </div>

      <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-3 max-w-3xl w-full">
        {[
          { label: "Health Score", desc: "Overall account grade from 0–100" },
          { label: "Wasted Spend", desc: "Exact dollars lost on poor performance" },
          { label: "Action Items", desc: "Prioritized fixes with AI explanations" },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-gray-200 p-6 text-left">
            <h3 className="font-semibold text-gray-900">{item.label}</h3>
            <p className="mt-1 text-sm text-gray-500">{item.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
