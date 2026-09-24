import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { VendorSalesPageContent } from "@/features/vendor-sales/components/VendorSalesPageContent";

export const metadata: Metadata = { title: "Your sales — Marketplace" };

export default function VendorSalesPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Your sales</h1>
        <p className="mt-2 text-muted">Every order placed against your store, and what you earned.</p>
        <div className="mt-8">
          <VendorSalesPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
