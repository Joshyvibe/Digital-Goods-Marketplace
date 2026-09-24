// Stripe Checkout Sessions can only be completed one at a time (each is a full-page
// redirect to Stripe), so a multi-vendor cart's N sessions are walked sequentially: redirect
// to the first, and when Stripe's success_url lands us back on /checkout/return, pop the
// next one and redirect again. sessionStorage is what survives the full-page redirects in
// between — nothing here is sensitive (just session URLs), so sessionStorage is fine.
const STORAGE_KEY = "pending_checkout";

interface PendingCheckout {
  orderId: number;
  remainingUrls: string[];
}

export function startPendingCheckout(orderId: number, urls: string[]) {
  const pending: PendingCheckout = { orderId, remainingUrls: urls };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(pending));
}

/** Call on /checkout/return load. Advances past the session we just returned from and
 * reports the next URL to redirect to, or null once the sequence is complete. */
export function advancePendingCheckout(): { orderId: number; nextUrl: string | null } | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  const pending: PendingCheckout = JSON.parse(raw);
  const remaining = pending.remainingUrls.slice(1);

  if (remaining.length > 0) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...pending, remainingUrls: remaining }));
    return { orderId: pending.orderId, nextUrl: remaining[0] };
  }

  sessionStorage.removeItem(STORAGE_KEY);
  return { orderId: pending.orderId, nextUrl: null };
}
