"use client";

import Script from "next/script";
import { useCallback, useEffect, useRef } from "react";
import { useAuth } from "../hooks/AuthContext";

// Google Identity Services — renders the official button and hands back a signed ID token
// (response.credential), which we forward to the backend for verification. Not an OAuth
// redirect flow, so there's no callback route to build on our side.
// https://developers.google.com/identity/gsi/web

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

interface GoogleSignInButtonProps {
  onError?: (message: string) => void;
  onSuccess?: () => void;
}

export function GoogleSignInButton({ onError, onSuccess }: GoogleSignInButtonProps) {
  const { loginWithGoogle } = useAuth();
  const buttonRef = useRef<HTMLDivElement>(null);

  const initializeButton = useCallback(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || !window.google || !buttonRef.current) return;

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        try {
          await loginWithGoogle(response.credential);
          onSuccess?.();
        } catch {
          onError?.("Google sign-in failed. Please try again.");
        }
      },
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      width: 320,
    });
  }, [loginWithGoogle, onError, onSuccess]);

  // <Script onLoad> only fires the *first* time this script tag ever loads on the page.
  // On a client-side (SPA) navigation to a different route that mounts a *new*
  // GoogleSignInButton — e.g. register -> login without a full page reload — the script is
  // already cached, so onLoad never re-fires for this instance and the button silently
  // never renders until a hard refresh restarts the whole load sequence. This effect
  // covers that case: if the script already loaded (from an earlier page in the same
  // session), initialize immediately instead of waiting for an onLoad that isn't coming.
  useEffect(() => {
    if (window.google) initializeButton();
  }, [initializeButton]);

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initializeButton}
      />
      <div ref={buttonRef} />
    </>
  );
}
