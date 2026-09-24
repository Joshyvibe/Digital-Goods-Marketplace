import { apiFetch } from "@/lib/apiClient";
import type { Paginated } from "@/types/api";
import type { ProductFile, ProductInput, VendorProduct } from "./types";

export async function listMyProducts(): Promise<Paginated<VendorProduct>> {
  return apiFetch("/api/vendors/products/");
}

export async function getMyProduct(id: number): Promise<VendorProduct> {
  return apiFetch(`/api/vendors/products/${id}/`);
}

export async function createProduct(input: ProductInput): Promise<VendorProduct> {
  return apiFetch("/api/vendors/products/", { body: input });
}

export async function updateProduct(
  id: number,
  input: Partial<ProductInput>
): Promise<VendorProduct> {
  return apiFetch(`/api/vendors/products/${id}/`, { method: "PATCH", body: input });
}

interface PresignResponse {
  upload_url: string;
  storage_key: string;
}

async function presignUpload(
  productId: number,
  filename: string,
  contentType: string
): Promise<PresignResponse> {
  return apiFetch(`/api/vendors/products/${productId}/presign-upload/`, {
    body: { filename, content_type: contentType },
  });
}

async function registerFile(
  productId: number,
  payload: { storage_key: string; original_filename: string; byte_size: number; content_type: string }
): Promise<ProductFile> {
  return apiFetch(`/api/vendors/products/${productId}/files/`, { body: payload });
}

export async function deleteFile(productId: number, fileId: number): Promise<void> {
  await apiFetch(`/api/vendors/products/${productId}/files/${fileId}/`, { method: "DELETE" });
}

/**
 * Full three-step upload: presign -> PUT the raw bytes directly to R2 (never through our
 * API) -> register the resulting file. The PUT uses plain fetch, not apiFetch — it's a
 * different origin (R2) that must never see our Authorization header or cookies.
 */
export async function uploadProductFile(productId: number, file: File): Promise<ProductFile> {
  const { upload_url, storage_key } = await presignUpload(productId, file.name, file.type);

  const putResponse = await fetch(upload_url, {
    method: "PUT",
    headers: { "Content-Type": file.type },
    body: file,
  });
  if (!putResponse.ok) {
    throw new Error("Upload to storage failed. Please try again.");
  }

  return registerFile(productId, {
    storage_key,
    original_filename: file.name,
    byte_size: file.size,
    content_type: file.type,
  });
}

/** Same presign+PUT mechanism as uploadProductFile, but the result is set as the
 * product's cover_image_key rather than registered as a downloadable ProductFile. */
export async function uploadCoverImage(productId: number, file: File): Promise<VendorProduct> {
  const { upload_url, storage_key } = await presignUpload(productId, file.name, file.type);

  const putResponse = await fetch(upload_url, {
    method: "PUT",
    headers: { "Content-Type": file.type },
    body: file,
  });
  if (!putResponse.ok) {
    throw new Error("Upload to storage failed. Please try again.");
  }

  return updateProduct(productId, { cover_image_key: storage_key });
}
