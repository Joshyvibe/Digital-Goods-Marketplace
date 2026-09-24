"use client";

import { CreditCard, Info, Loader2, ShoppingBag, Store, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { FormError } from "@/components/ui/FormError";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { startCheckout } from "@/features/checkout/api";
import { startPendingCheckout } from "@/features/checkout/pendingCheckout";
import { ApiError } from "@/types/api";
import { useCart } from "../hooks/CartContext";
import type { CartItem } from "../types";

function formatPrice(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100
  );
}

function groupByVendor(items: CartItem[]) {
  const groups = new Map<string, CartItem[]>();
  for (const item of items) {
    const list = groups.get(item.vendor_store_name) ?? [];
    list.push(item);
    groups.set(item.vendor_store_name, list);
  }
  return groups;
}

export function CartPageContent() {
  const { user, isLoading: authLoading } = useAuth();
  const { cart, isLoading: cartLoading, removeFromCart } = useCart();
  const [error, setError] = useState<string | null>(null);
  const [isCheckingOut, setIsCheckingOut] = useState(false);

  if (authLoading || cartLoading) {
    return <Spinner label="Loading your cart…" />;
  }

  if (!user) {
    return (
      <p className="text-muted">
        <Link href="/login" className="font-semibold text-ink underline underline-offset-2">
          Sign in
        </Link>{" "}
        to view your cart.
      </p>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center">
        <ShoppingBag className="h-8 w-8 text-muted" strokeWidth={1.5} />
        <p className="text-muted">Your cart is empty.</p>
        <Link
          href="/products"
          className="mt-1 inline-block rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper"
        >
          Browse products
        </Link>
      </div>
    );
  }

  const vendorGroups = groupByVendor(cart.items);
  const vendorCount = vendorGroups.size;

  const handleCheckout = async () => {
    setError(null);
    setIsCheckingOut(true);
    try {
      const { order_id, checkout_urls } = await startCheckout();
      if (checkout_urls.length === 0) throw new Error("No checkout sessions were created.");
      startPendingCheckout(order_id, checkout_urls);
      window.location.href = checkout_urls[0];
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start checkout. Please try again.");
      setIsCheckingOut(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {vendorCount > 1 && (
        <p className="flex items-start gap-2 rounded-xl bg-paper-muted p-4 text-sm text-ink/80">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted" strokeWidth={2} />
          Your cart spans {vendorCount} shops — you&rsquo;ll complete {vendorCount} separate
          charges, one per shop, right after each other.
        </p>
      )}

      <div className="flex flex-col gap-6">
        {[...vendorGroups.entries()].map(([vendorName, items]) => (
          <div key={vendorName} className="rounded-2xl border border-line p-5">
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted">
              <Store className="h-4 w-4" strokeWidth={2} />
              {vendorName}
            </p>
            <ul className="flex flex-col gap-3">
              <AnimatePresence initial={false}>
                {items.map((item) => (
                  <motion.li
                    key={item.id}
                    layout
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    className="flex items-center justify-between overflow-hidden"
                  >
                    <Link href={`/products/${item.slug}`} className="hover:underline">
                      {item.title}
                    </Link>
                    <div className="flex items-center gap-4">
                      <span className="font-semibold">
                        {formatPrice(item.price_cents, item.currency)}
                      </span>
                      <button
                        onClick={() => removeFromCart(item.product_id)}
                        aria-label={`Remove ${item.title}`}
                        className="text-red-600 transition hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" strokeWidth={1.8} />
                      </button>
                    </div>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-line pt-6">
        <span className="text-lg font-bold">Total</span>
        <span className="text-lg font-bold">{formatPrice(cart.total_cents, "usd")}</span>
      </div>

      <FormError message={error} />

      <button
        onClick={handleCheckout}
        disabled={isCheckingOut}
        className="flex items-center justify-center gap-2 self-start rounded-full bg-accent px-8 py-3 font-semibold text-accent-ink transition hover:brightness-95 active:scale-[0.98] disabled:opacity-50"
      >
        {isCheckingOut ? (
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
        ) : (
          <CreditCard className="h-4 w-4" strokeWidth={2} />
        )}
        {isCheckingOut ? "Starting checkout…" : "Checkout"}
      </button>
    </div>
  );
}
