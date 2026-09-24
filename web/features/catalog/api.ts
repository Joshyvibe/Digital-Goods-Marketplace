import { apiFetch } from "@/lib/apiClient";
import type { Paginated } from "@/types/api";
import type { Product } from "./types";

// Public catalog endpoints hit PublicProductViewSet (api/apps/catalog) — no auth required.

export async function listProducts(params: { search?: string; category?: string } = {}) {
  const query = new URLSearchParams(params as Record<string, string>).toString();
  return apiFetch<Paginated<Product>>(`/api/products/${query ? `?${query}` : ""}`, { skipAuth: true });
}

export async function getProduct(slug: string) {
  return apiFetch<Product>(`/api/products/${slug}/`, { skipAuth: true });
}

export interface VendorStorefront {
  store_name: string;
  slug: string;
  products: Product[];
}

export async function getVendorStorefront(slug: string) {
  return apiFetch<VendorStorefront>(`/api/store/${slug}/`, { skipAuth: true });
}
