import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { VendorProductsPageContent } from "@/features/vendor-products/components/VendorProductsPageContent";

export const metadata: Metadata = { title: "Your products — Marketplace" };

export default function VendorProductsPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Your products</h1>
        <div className="mt-8">
          <VendorProductsPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
