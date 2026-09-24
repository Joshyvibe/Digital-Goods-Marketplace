import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { OrderListPageContent } from "@/features/orders/components/OrderListPageContent";

export const metadata: Metadata = { title: "Your orders — Marketplace" };

export default function OrdersPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Your orders</h1>
        <div className="mt-8">
          <OrderListPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
