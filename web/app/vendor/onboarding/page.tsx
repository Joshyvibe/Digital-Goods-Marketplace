import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Spinner } from "@/components/ui/Spinner";
import { OnboardingFlow } from "@/features/vendor-onboarding/components/OnboardingFlow";

export const metadata: Metadata = { title: "Start selling — Marketplace" };

export default function VendorOnboardingPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-lg flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Start selling</h1>
        <p className="mt-2 text-muted">Set up payouts with Stripe to publish your first product.</p>
        <div className="mt-8">
          <Suspense fallback={<Spinner />}>
            <OnboardingFlow />
          </Suspense>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
