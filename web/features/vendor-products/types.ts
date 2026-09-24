export type ProductStatus = "draft" | "published" | "archived";
export type ProductCategory = "template" | "preset" | "ebook" | "license" | "stock";

export interface ProductFile {
  id: number;
  original_filename: string;
  byte_size: number;
  content_type: string;
  sort_order: number;
}

export interface VendorProduct {
  id: number;
  title: string;
  slug: string;
  description: string;
  category: ProductCategory;
  price_cents: number;
  currency: string;
  status: ProductStatus;
  cover_image_key: string;
  cover_image_url: string | null;
  files: ProductFile[];
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  title: string;
  description: string;
  category: ProductCategory;
  price_cents: number;
  status?: ProductStatus;
  cover_image_key?: string;
}
