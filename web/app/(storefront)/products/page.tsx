import type { Metadata } from "next";
import { PackageOpen } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { listProducts } from "@/features/catalog/api";
import { AnimatedProductGrid } from "@/features/catalog/components/AnimatedProductGrid";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "All products — Marketplace" };

export default async function ProductsPage() {
  const { results: products } = await listProducts().catch(() => ({ results: [] }));

  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">All products</h1>
        <p className="mt-2 text-muted">{products.length} products from independent creators.</p>

        {products.length === 0 ? (
          <div className="mt-10 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center text-muted">
            <PackageOpen className="h-8 w-8" strokeWidth={1.5} />
            <p>No products published yet.</p>
          </div>
        ) : (
          <div className="mt-10">
            <AnimatedProductGrid products={products} />
          </div>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
