import { AuthCard } from "@/components/auth/auth-card";

export default function LoginPage({
  searchParams,
}: {
  searchParams?: { [key: string]: string | string[] | undefined };
}) {
  const next = typeof searchParams?.next === "string" ? searchParams.next : "/dashboard";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.18),_transparent_36%),linear-gradient(180deg,_#f8fafc,_#eef2ff)] px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center gap-10 lg:grid lg:grid-cols-[1.1fr_0.9fr]">
        <section className="hidden rounded-[2rem] bg-slate-950 p-10 text-white lg:block">
          <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">Phase 2</p>
          <h2 className="mt-4 text-4xl font-semibold leading-tight">
            Secure platform auth plus a clean Meta Ads connection flow.
          </h2>
          <div className="mt-8 space-y-4 text-sm text-slate-300">
            <p>Register or sign in, connect Meta through OAuth, and pick the ad account you want to audit.</p>
            <p>Tokens stay encrypted at rest in PostgreSQL and the dashboard stays protected behind JWT auth.</p>
          </div>
        </section>
        <AuthCard mode="login" nextHref={next} />
      </div>
    </main>
  );
}
