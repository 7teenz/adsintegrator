import type { Metadata } from "next";
import { SentryInit } from "@/components/app/sentry-init";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meta Ads Audit - Find Wasted Ad Spend",
  description:
    "Upload your Ads Manager export, audit performance, and surface wasted spend opportunities fast.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-900 antialiased">
        <SentryInit />
        {children}
      </body>
    </html>
  );
}
