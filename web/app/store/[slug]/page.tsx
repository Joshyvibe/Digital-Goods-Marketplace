import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { PackageOpen, Store } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { getVendorStorefront } from "@/features/catalog/api";
import { AnimatedProductGrid } from "@/features/catalog/components/AnimatedProductGrid";
import { ApiError } from "@/types/api";

export const dynamic = "force-dynamic";

async function loadStore(slug: string) {
  return getVendorStorefront(slug).catch((err) => {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  });
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const store = await loadStore(slug);
  return { title: store ? `${store.store_name} — Marketplace` : "Store not found" };
}

export default async function VendorStorefrontPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const store = await loadStore(slug);

  if (!store) notFound();

  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-16">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-ink text-paper">
            <Store className="h-6 w-6" strokeWidth={1.75} />
          </span>
          <div>
            <h1 className="text-3xl font-black tracking-tight uppercase sm:text-4xl">
              {store.store_name}
            </h1>
            <p className="text-muted">
              {store.products.length} product{store.products.length === 1 ? "" : "s"}
            </p>
          </div>
        </div>

        {store.products.length === 0 ? (
          <div className="mt-10 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center text-muted">
            <PackageOpen className="h-8 w-8" strokeWidth={1.5} />
            <p>No products published yet.</p>
          </div>
        ) : (
          <div className="mt-10">
            <AnimatedProductGrid products={store.products} />
          </div>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
