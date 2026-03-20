"use client";

import { useEffect } from "react";

let sentryInitialized = false;

export function SentryInit() {
  useEffect(() => {
    async function init() {
      const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
      if (!dsn || sentryInitialized) return;

      const Sentry = await import("@sentry/browser");
      Sentry.init({
        dsn,
        environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "local",
        tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || "0"),
      });
      sentryInitialized = true;
    }

    void init();
  }, []);

  return null;
}
