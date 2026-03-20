"use client";

interface Props {
  score: number;
  size?: "sm" | "lg";
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  if (score >= 40) return "text-orange-600";
  return "text-rose-600";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Healthy";
  if (score >= 40) return "Watchlist";
  return "Critical";
}

function ringColor(score: number): string {
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  if (score >= 40) return "#ea580c";
  return "#e11d48";
}

export function HealthScore({ score, size = "lg" }: Props) {
  const large = size === "lg";
  const radius = large ? 68 : 34;
  const stroke = large ? 8 : 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
  const dimension = (radius + stroke) * 2;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={dimension} height={dimension} className="-rotate-90">
        <circle cx={radius + stroke} cy={radius + stroke} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={radius + stroke}
          cy={radius + stroke}
          r={radius}
          fill="none"
          stroke={ringColor(score)}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${large ? "text-4xl" : "text-xl"} font-bold ${scoreColor(score)}`}>{Math.round(score)}</span>
        <span className={`${large ? "text-sm" : "text-xs"} text-slate-500`}>{scoreLabel(score)}</span>
      </div>
    </div>
  );
}
