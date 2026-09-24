import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { listProducts } from "@/features/catalog/api";
import { FeaturedCollection } from "@/features/catalog/components/FeaturedCollection";
import { Hero } from "@/features/catalog/components/Hero";

// Catalog data changes whenever a vendor publishes/unpublishes a product — this page must
// reflect current DB state on every request, not the state at last build.
export const dynamic = "force-dynamic";

export default async function StorefrontPage() {
  const { results: products } = await listProducts().catch(() => ({ results: [] }));

  return (
    <>
      <SiteHeader />
      <main className="flex flex-1 flex-col">
        <Hero />
        <div id="featured">
          <FeaturedCollection products={products} />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
