import { PackageOpen } from "lucide-react";
import Link from "next/link";
import type { Product } from "../types";
import { AnimatedProductGrid } from "./AnimatedProductGrid";

export function FeaturedCollection({ products }: { products: Product[] }) {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-20">
      <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black tracking-tight uppercase">Featured this week</h2>
          <p className="mt-2 max-w-md text-muted">
            Templates, presets, and ebooks — hand-picked from independent creators.
          </p>
        </div>
        <Link
          href="/products"
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-accent-ink transition hover:brightness-95"
        >
          Shop all
        </Link>
      </div>

      {products.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center text-muted">
          <PackageOpen className="h-8 w-8" strokeWidth={1.5} />
          <p>
            No products published yet — run <code>seed_demo</code> or publish one from a vendor
            account.
          </p>
        </div>
      ) : (
        <AnimatedProductGrid products={products} />
      )}
    </section>
  );
}
