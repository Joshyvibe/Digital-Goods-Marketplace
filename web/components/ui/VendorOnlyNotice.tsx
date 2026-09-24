import { Store } from "lucide-react";
import Link from "next/link";

export function VendorOnlyNotice() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line p-12 text-center">
      <Store className="h-8 w-8 text-muted" strokeWidth={1.5} />
      <p className="text-muted">You&rsquo;re not a vendor yet.</p>
      <Link
        href="/vendor/onboarding"
        className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper transition hover:bg-ink/85"
      >
        Start selling
      </Link>
    </div>
  );
}
