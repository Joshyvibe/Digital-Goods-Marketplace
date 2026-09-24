import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Spinner } from "@/components/ui/Spinner";
import { CheckoutReturnFlow } from "@/features/checkout/components/CheckoutReturnFlow";

export const metadata: Metadata = { title: "Checkout — Marketplace" };

export default function CheckoutReturnPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <Suspense fallback={<Spinner />}>
          <CheckoutReturnFlow />
        </Suspense>
      </main>
      <SiteFooter />
    </>
  );
}
