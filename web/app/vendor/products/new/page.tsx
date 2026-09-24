import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { NewProductPageContent } from "@/features/vendor-products/components/NewProductPageContent";

export const metadata: Metadata = { title: "New product — Marketplace" };

export default function NewVendorProductPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-lg flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">New product</h1>
        <p className="mt-2 text-muted">Saved as a draft — publish once you&rsquo;re ready.</p>
        <div className="mt-8">
          <NewProductPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
