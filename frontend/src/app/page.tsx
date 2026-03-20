import Link from "next/link";

import { Hero } from "@/components/landing/hero";

export default function LandingPage() {
  return (
    <main>
      <nav className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
        <span className="text-lg font-bold text-gray-900">Meta Ads Audit</span>
        <Link href="/login" className="text-sm font-medium text-brand-600 hover:text-brand-700">
          Sign In
        </Link>
      </nav>
      <Hero />
    </main>
  );
}
