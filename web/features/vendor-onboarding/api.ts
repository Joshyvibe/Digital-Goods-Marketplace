import { apiFetch } from "@/lib/apiClient";
import { ApiError } from "@/types/api";
import type { VendorProfile } from "./types";

export async function startOnboarding(storeName: string): Promise<{ onboarding_url: string }> {
  return apiFetch("/api/vendors/onboard/", { body: { store_name: storeName } });
}

export async function getOnboardingStatus(): Promise<VendorProfile | null> {
  try {
    return await apiFetch<VendorProfile>("/api/vendors/onboarding-status/");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export async function updateStoreName(storeName: string): Promise<VendorProfile> {
  return apiFetch<VendorProfile>("/api/vendors/onboarding-status/", {
    method: "PATCH",
    body: { store_name: storeName },
  });
}
