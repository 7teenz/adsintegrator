import { AuthCard } from "@/components/auth/auth-card";

export default function RegisterPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.18),_transparent_36%),linear-gradient(180deg,_#f8fafc,_#eef2ff)] px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center">
        <AuthCard mode="register" nextHref="/dashboard" />
      </div>
    </main>
  );
}
