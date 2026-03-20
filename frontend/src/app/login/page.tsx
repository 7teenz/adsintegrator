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
          <h2 className="mt-4 text-4xl font-semibold leading-tight">
            Audit upload-first accounts without another spreadsheet-heavy workflow.
          </h2>
          <div className="mt-8 space-y-4 text-sm text-slate-300">
            <p>Sign in to upload your Ads Manager export, review account health, and generate a focused audit report.</p>
            <p>Your account stays protected and your connected Meta credentials are stored encrypted at rest.</p>
          </div>
        </section>
        <AuthCard mode="login" nextHref={next} />
      </div>
    </main>
  );
}
