"use client";

import { CircleUserRound, LogOut, Menu, ShoppingBag, X } from "lucide-react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/features/auth/hooks/AuthContext";
import { useCart } from "@/features/cart/hooks/CartContext";

export function SiteHeader() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const itemCount = cart?.items.length ?? 0;
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!isMenuOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!headerRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [isMenuOpen]);

  const navLinks = [
    { href: "/", label: "Shop" },
    user?.is_vendor
      ? { href: "/vendor/products", label: "My Products" }
      : { href: "/vendor/onboarding", label: "Sell" },
    ...(user ? [{ href: "/orders", label: "Orders" }] : []),
    ...(user?.is_vendor ? [{ href: "/vendor/sales", label: "Sales" }] : []),
  ];

  const closeMenu = () => setIsMenuOpen(false);

  return (
    <header ref={headerRef} className="sticky top-0 z-40 border-b border-line bg-paper/90 backdrop-blur">
      <div className="bg-ink px-4 py-2 text-center text-xs font-medium tracking-wide text-paper">
        New this week — templates, presets & ebooks from independent creators
      </div>
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="text-lg font-black tracking-tight uppercase" onClick={closeMenu}>
          Marketplace
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium sm:flex">
          {navLinks.map((link) => (
            <Link key={link.href} href={link.href} className="text-ink/70 transition hover:text-ink">
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          <Link
            href="/cart"
            className="relative flex items-center text-ink/70 transition hover:text-ink"
            aria-label="Cart"
            onClick={closeMenu}
          >
            <ShoppingBag className="h-5 w-5" strokeWidth={1.8} />
            <AnimatePresence>
              {itemCount > 0 && (
                <motion.span
                  key={itemCount}
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.5, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 500, damping: 20 }}
                  className="absolute -top-2 -right-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-accent-ink"
                >
                  {itemCount}
                </motion.span>
              )}
            </AnimatePresence>
          </Link>
          {user ? (
            <>
              <Link
                href="/account"
                className="hidden items-center gap-1.5 text-sm font-medium text-ink/70 transition hover:text-ink sm:flex"
              >
                <CircleUserRound className="h-4 w-4" strokeWidth={1.8} />
                Account
              </Link>
              <button
                onClick={() => logout()}
                className="hidden items-center gap-1.5 text-sm font-medium text-ink/70 transition hover:text-ink sm:flex"
              >
                <LogOut className="h-4 w-4" strokeWidth={1.8} />
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden text-sm font-medium text-ink/70 transition hover:text-ink sm:block"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="hidden rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink/85 sm:inline-flex"
              >
                Get started
              </Link>
            </>
          )}

          <button
            onClick={() => setIsMenuOpen((open) => !open)}
            aria-label={isMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMenuOpen}
            className="relative flex h-8 w-8 items-center justify-center text-ink sm:hidden"
          >
            <AnimatePresence initial={false} mode="wait">
              <motion.span
                key={isMenuOpen ? "close" : "open"}
                initial={{ opacity: 0, rotate: -45 }}
                animate={{ opacity: 1, rotate: 0 }}
                exit={{ opacity: 0, rotate: 45 }}
                transition={{ duration: 0.18 }}
                className="absolute inset-0 flex items-center justify-center"
              >
                {isMenuOpen ? (
                  <X className="h-5 w-5" strokeWidth={2} />
                ) : (
                  <Menu className="h-5 w-5" strokeWidth={2} />
                )}
              </motion.span>
            </AnimatePresence>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden border-t border-line bg-paper sm:hidden"
          >
            <nav className="flex flex-col gap-1 px-4 py-4 text-base font-medium">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={closeMenu}
                  className="rounded-xl px-3 py-2.5 text-ink/80 transition hover:bg-paper-muted hover:text-ink"
                >
                  {link.label}
                </Link>
              ))}

              <div className="my-2 border-t border-line" />

              {user ? (
                <>
                  <Link
                    href="/account"
                    onClick={closeMenu}
                    className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-ink/80 transition hover:bg-paper-muted hover:text-ink"
                  >
                    <CircleUserRound className="h-4 w-4" strokeWidth={1.8} />
                    Account
                  </Link>
                  <button
                    onClick={() => {
                      closeMenu();
                      logout();
                    }}
                    className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-ink/80 transition hover:bg-paper-muted hover:text-ink"
                  >
                    <LogOut className="h-4 w-4" strokeWidth={1.8} />
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    onClick={closeMenu}
                    className="rounded-xl px-3 py-2.5 text-ink/80 transition hover:bg-paper-muted hover:text-ink"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    onClick={closeMenu}
                    className="mt-1 rounded-full bg-ink px-4 py-2.5 text-center font-semibold text-paper transition hover:bg-ink/85"
                  >
                    Get started
                  </Link>
                </>
              )}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
