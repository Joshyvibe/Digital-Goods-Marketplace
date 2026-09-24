export interface CartItem {
  id: number;
  product_id: number;
  title: string;
  slug: string;
  price_cents: number;
  currency: string;
  vendor_store_name: string;
}

export interface Cart {
  id: number;
  status: "open" | "converted";
  items: CartItem[];
  total_cents: number;
  vendor_count: number;
}
