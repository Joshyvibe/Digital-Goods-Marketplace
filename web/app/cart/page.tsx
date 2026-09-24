import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { CartPageContent } from "@/features/cart/components/CartPageContent";

export const metadata: Metadata = { title: "Your cart — Marketplace" };

export default function CartPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
        <h1 className="text-3xl font-black tracking-tight uppercase">Your cart</h1>
        <div className="mt-8">
          <CartPageContent />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
