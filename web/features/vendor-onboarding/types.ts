export type OnboardingStatus = "not_started" | "pending" | "complete" | "restricted";

export interface VendorProfile {
  store_name: string;
  slug: string;
  onboarding_status: OnboardingStatus;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  is_onboarded: boolean;
}
