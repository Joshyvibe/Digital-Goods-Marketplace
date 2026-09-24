import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { OrderDetailPageContent } from "@/features/orders/components/OrderDetailPageContent";

export const metadata: Metadata = { title: "Order details — Marketplace" };

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <OrderDetailPageContent orderId={Number(id)} />
      </main>
      <SiteFooter />
    </>
  );
}
