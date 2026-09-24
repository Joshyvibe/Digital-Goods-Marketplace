import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ProductEditPageContent } from "@/features/vendor-products/components/ProductEditPageContent";

export const metadata: Metadata = { title: "Edit product — Marketplace" };

export default async function VendorProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Edit product</h1>
        <div className="mt-8">
          <ProductEditPageContent productId={Number(id)} />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
