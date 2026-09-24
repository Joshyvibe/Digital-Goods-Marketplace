"use client";

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  Store,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { FormError } from "@/components/ui/FormError";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { ApiError } from "@/types/api";
import { getOnboardingStatus, startOnboarding } from "../api";
import type { VendorProfile } from "../types";

const STATUS_COPY: Record<
  VendorProfile["onboarding_status"],
  { label: string; tone: string; icon: typeof CheckCircle2 }
> = {
  not_started: { label: "Not started", tone: "text-muted", icon: Circle },
  pending: { label: "Onboarding in progress", tone: "text-amber-600", icon: Clock },
  complete: { label: "Ready to sell", tone: "text-emerald-600", icon: CheckCircle2 },
  restricted: { label: "Action needed", tone: "text-red-600", icon: AlertTriangle },
};

export function OnboardingFlow() {
  const { user, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const isReturning = searchParams.get("return") === "1";
  const isRefreshing = searchParams.get("refresh") === "1";

  const [vendor, setVendor] = useState<VendorProfile | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [storeName, setStoreName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const autoRefreshFired = useRef(false);

  useEffect(() => {
    if (authLoading || !user) return;
    getOnboardingStatus()
      .then(setVendor)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load status."))
      .finally(() => setStatusLoading(false));
  }, [authLoading, user]);

  const goToStripe = async (name: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      const { onboarding_url } = await startOnboarding(name);
      window.location.href = onboarding_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start onboarding.");
      setIsSubmitting(false);
    }
  };

  // The refresh_url leg of Stripe's AccountLink flow: AccountLinks are single-use and
  // short-lived, so landing here means the previous one expired — mint a new one and go
  // straight back into Stripe with no user interaction required.
  useEffect(() => {
    if (isRefreshing && vendor && !autoRefreshFired.current) {
      autoRefreshFired.current = true;
      goToStripe(vendor.store_name);
    }
  }, [isRefreshing, vendor]);

  if (authLoading || statusLoading || (isRefreshing && vendor)) {
    return <Spinner label={isRefreshing ? "Redirecting to Stripe…" : "Loading…"} />;
  }

  if (!user) {
    return <p className="text-muted">Sign in to start selling.</p>;
  }

  if (!vendor) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-ink/80">
          Tell us your store name — we&rsquo;ll set up a Stripe Express account so you can get
          paid directly.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            goToStripe(storeName);
          }}
          className="flex flex-col gap-4"
        >
          <TextField
            label="Store name"
            icon={Store}
            required
            value={storeName}
            onChange={(e) => setStoreName(e.target.value)}
            placeholder="Studio North"
          />
          <FormError message={error} />
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center justify-center gap-2 rounded-full bg-ink px-4 py-2.5 font-semibold text-paper transition hover:bg-ink/85 active:scale-[0.98] disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
            ) : (
              <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
            )}
            {isSubmitting ? "Redirecting to Stripe…" : "Continue to Stripe"}
          </button>
        </form>
      </div>
    );
  }

  const { label, tone, icon: StatusIcon } = STATUS_COPY[vendor.onboarding_status];

  return (
    <div className="flex flex-col gap-6">
      {isReturning && (
        <p className="rounded-xl bg-paper-muted p-4 text-sm text-ink/80">
          Welcome back — here&rsquo;s your current status.
        </p>
      )}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="rounded-2xl border border-line p-6"
      >
        <p className="text-sm font-medium text-muted">{vendor.store_name}</p>
        <p className={`mt-1 flex items-center gap-2 text-xl font-bold ${tone}`}>
          <StatusIcon className="h-5 w-5" strokeWidth={2.2} />
          {label}
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-muted">Charges</dt>
            <dd className="font-semibold">{vendor.charges_enabled ? "Enabled" : "Not yet"}</dd>
          </div>
          <div>
            <dt className="text-muted">Payouts</dt>
            <dd className="font-semibold">{vendor.payouts_enabled ? "Enabled" : "Not yet"}</dd>
          </div>
        </dl>
      </motion.div>

      <FormError message={error} />

      {vendor.is_onboarded ? (
        <Link
          href="/vendor/products"
          className="flex items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 text-center font-semibold text-paper transition hover:bg-ink/85"
        >
          Go to your products
          <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
        </Link>
      ) : (
        <button
          onClick={() => goToStripe(vendor.store_name)}
          disabled={isSubmitting}
          className="flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3 font-semibold text-accent-ink transition hover:brightness-95 active:scale-[0.98] disabled:opacity-50"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />}
          {isSubmitting ? "Redirecting to Stripe…" : "Continue onboarding"}
        </button>
      )}
    </div>
  );
}
