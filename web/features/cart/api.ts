import { apiFetch } from "@/lib/apiClient";
import type { Cart } from "./types";

export async function getCart(): Promise<Cart> {
  return apiFetch("/api/cart/");
}

export async function addToCart(productId: number): Promise<Cart> {
  return apiFetch("/api/cart/items/", { body: { product_id: productId } });
}

export async function removeFromCart(productId: number): Promise<Cart> {
  return apiFetch(`/api/cart/items/${productId}/`, { method: "DELETE" });
}
