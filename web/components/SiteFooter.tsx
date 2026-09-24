import { Mail, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line bg-paper-muted">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-12 sm:flex-row sm:justify-between">
        <div className="flex flex-col gap-3">
          <Link href="/" className="text-lg font-black tracking-tight uppercase">
            Marketplace
          </Link>
          <p className="max-w-xs text-sm text-muted">
            Templates, presets, ebooks, and licenses from independent creators — delivered instantly.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-muted">
            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2} />
            Payments secured by Stripe Connect
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8 sm:flex sm:gap-16">
          <div className="flex flex-col gap-2 text-sm">
            <p className="font-semibold">Shop</p>
            <Link href="/" className="text-muted transition hover:text-ink">
              Browse
            </Link>
            <Link href="/orders" className="text-muted transition hover:text-ink">
              Your orders
            </Link>
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <p className="font-semibold">Sell</p>
            <Link href="/vendor/onboarding" className="text-muted transition hover:text-ink">
              Become a vendor
            </Link>
            <Link href="/vendor/products" className="text-muted transition hover:text-ink">
              Manage products
            </Link>
          </div>
        </div>
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-muted sm:flex-row">
          <p className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" strokeWidth={2} />
            &copy; {new Date().getFullYear()} Marketplace. Built as a portfolio project.
          </p>
          <a href="mailto:hello@marketplace.example" className="flex items-center gap-1.5 hover:text-ink">
            <Mail className="h-3.5 w-3.5" strokeWidth={2} />
            hello@marketplace.example
          </a>
        </div>
      </div>
    </footer>
  );
}
