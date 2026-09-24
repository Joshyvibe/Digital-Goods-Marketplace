"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import * as cartApi from "../api";
import type { Cart } from "../types";

interface CartContextValue {
  cart: Cart | null;
  isLoading: boolean;
  addToCart: (productId: number) => Promise<void>;
  removeFromCart: (productId: number) => Promise<void>;
  refresh: () => Promise<void>;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
  const { user, isLoading: authLoading } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) {
      setCart(null);
      return;
    }
    const data = await cartApi.getCart();
    setCart(data);
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    // Route every branch through a microtask (never setState synchronously in the effect
    // body itself) — react-hooks/set-state-in-effect flags the synchronous form because it
    // forces an extra render before paint.
    Promise.resolve()
      .then(() => (user ? cartApi.getCart() : null))
      .then(setCart)
      .finally(() => setIsLoading(false));
  }, [authLoading, user]);

  const addToCart = async (productId: number) => {
    const updated = await cartApi.addToCart(productId);
    setCart(updated);
  };

  const removeFromCart = async (productId: number) => {
    const updated = await cartApi.removeFromCart(productId);
    setCart(updated);
  };

  return (
    <CartContext.Provider value={{ cart, isLoading, addToCart, removeFromCart, refresh }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
