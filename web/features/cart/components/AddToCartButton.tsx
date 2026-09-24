"use client";

import { CheckCircle2, Loader2, LogIn, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { FormError } from "@/components/ui/FormError";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { useCart } from "@/features/cart/hooks/CartContext";
import { ApiError } from "@/types/api";

export function AddToCartButton({ productId }: { productId: number }) {
  const { user } = useAuth();
  const { cart, addToCart } = useCart();
  const [error, setError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const alreadyInCart = cart?.items.some((item) => item.product_id === productId) ?? false;

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex w-full items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 font-semibold text-paper transition hover:bg-ink/85"
      >
        <LogIn className="h-4 w-4" strokeWidth={2} />
        Sign in to buy
      </Link>
    );
  }

  const handleClick = async () => {
    setError(null);
    setIsAdding(true);
    try {
      await addToCart(productId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add to cart.");
    } finally {
      setIsAdding(false);
    }
  };

  if (alreadyInCart) {
    return (
      <Link
        href="/cart"
        className="flex w-full items-center justify-center gap-2 rounded-full bg-accent px-6 py-3 font-semibold text-accent-ink transition hover:brightness-95"
      >
        <CheckCircle2 className="h-4 w-4" strokeWidth={2.2} />
        In your cart — view cart
      </Link>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleClick}
        disabled={isAdding}
        className="flex w-full items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 font-semibold text-paper transition hover:bg-ink/85 active:scale-[0.98] disabled:opacity-50"
      >
        {isAdding ? (
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
        ) : (
          <ShoppingCart className="h-4 w-4" strokeWidth={2} />
        )}
        {isAdding ? "Adding…" : "Add to cart"}
      </button>
      <FormError message={error} />
    </div>
  );
}
