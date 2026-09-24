"use client";

import { AlertTriangle, CheckCircle2, Circle, Clock, LogOut, Mail, Package, Store } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ShareStoreLink } from "@/components/ShareStoreLink";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { getOnboardingStatus } from "@/features/vendor-onboarding/api";
import type { VendorProfile } from "@/features/vendor-onboarding/types";
import { DeleteAccountSection } from "./DeleteAccountSection";
import { StoreNameEditor } from "./StoreNameEditor";

const STATUS_COPY: Record<
  VendorProfile["onboarding_status"],
  { label: string; tone: string; icon: typeof CheckCircle2 }
> = {
  not_started: { label: "Not started", tone: "text-muted", icon: Circle },
  pending: { label: "Onboarding in progress", tone: "text-amber-600", icon: Clock },
  complete: { label: "Ready to sell", tone: "text-emerald-600", icon: CheckCircle2 },
  restricted: { label: "Action needed", tone: "text-red-600", icon: AlertTriangle },
};

export function AccountPageContent() {
  const { user, isLoading: authLoading, logout } = useAuth();
  const [vendor, setVendor] = useState<VendorProfile | null>(null);
  const [vendorLoading, setVendorLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    // Routed through a microtask — never setState synchronously in the effect body
    // itself (react-hooks/set-state-in-effect).
    Promise.resolve()
      .then(() => (user.is_vendor ? getOnboardingStatus() : null))
      .then(setVendor)
      .finally(() => setVendorLoading(false));
  }, [authLoading, user]);

  if (authLoading) return <Spinner />;

  if (!user) {
    return (
      <p className="text-muted">
        <Link href="/login" className="font-semibold text-ink underline underline-offset-2">
          Sign in
        </Link>{" "}
        to view your account.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-line p-6">
        <p className="flex items-center gap-1.5 text-sm text-muted">
          <Mail className="h-3.5 w-3.5" strokeWidth={2} />
          Signed in as
        </p>
        <p className="break-all text-lg font-semibold">{user.email}</p>
        <p className="mt-1 text-sm text-muted">
          {user.has_usable_password ? "Email & password" : "Google account"}
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/orders"
          className="flex flex-1 items-start gap-3 rounded-2xl border border-line p-5 transition hover:border-ink hover:shadow-sm"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-paper-muted">
            <Package className="h-4 w-4 text-ink" strokeWidth={2} />
          </span>
          <div>
            <p className="font-semibold">Your orders</p>
            <p className="mt-1 text-sm text-muted">View purchases and downloads</p>
          </div>
        </Link>

        {!authLoading && !vendorLoading && !user.is_vendor && (
          <Link
            href="/vendor/onboarding"
            className="flex flex-1 items-start gap-3 rounded-2xl border border-line p-5 transition hover:border-ink hover:shadow-sm"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-paper-muted">
              <Store className="h-4 w-4 text-ink" strokeWidth={2} />
            </span>
            <div>
              <p className="font-semibold">Become a vendor</p>
              <p className="mt-1 text-sm text-muted">Set up payouts and start selling</p>
            </div>
          </Link>
        )}
      </div>

      {user.is_vendor && (
        <div className="rounded-2xl border border-line p-6">
          <div className="flex items-center justify-between">
            {vendor ? (
              <StoreNameEditor vendor={vendor} onSaved={setVendor} />
            ) : (
              <p className="font-semibold">Your store</p>
            )}
            {vendor &&
              (() => {
                const { label, tone, icon: StatusIcon } = STATUS_COPY[vendor.onboarding_status];
                return (
                  <span className={`flex items-center gap-1.5 text-sm font-semibold ${tone}`}>
                    <StatusIcon className="h-4 w-4" strokeWidth={2.2} />
                    {label}
                  </span>
                );
              })()}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/vendor/products"
              className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper transition hover:bg-ink/85"
            >
              Manage products
            </Link>
            <Link
              href="/vendor/sales"
              className="rounded-full border border-line px-5 py-2 text-sm font-semibold transition hover:border-ink"
            >
              View sales
            </Link>
            <Link
              href="/vendor/onboarding"
              className="rounded-full border border-line px-5 py-2 text-sm font-semibold transition hover:border-ink"
            >
              Payout settings
            </Link>
          </div>
          {vendor && (
            <div className="mt-5 border-t border-line pt-5">
              <ShareStoreLink slug={vendor.slug} />
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => logout()}
        className="flex items-center gap-1.5 self-start text-sm font-semibold text-ink/70 transition hover:text-ink hover:underline"
      >
        <LogOut className="h-4 w-4" strokeWidth={1.8} />
        Sign out
      </button>

      <div className="border-t border-line pt-6">
        <DeleteAccountSection isVendor={user.is_vendor} />
      </div>
    </div>
  );
}
