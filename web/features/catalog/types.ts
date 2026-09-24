export interface Product {
  id: number;
  vendor_store_name: string;
  vendor_slug: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  price_cents: number;
  currency: string;
  cover_image_url: string | null;
}
