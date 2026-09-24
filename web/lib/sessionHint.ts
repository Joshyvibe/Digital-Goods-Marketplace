// The real refresh token is an HttpOnly cookie set by the Django API's own origin — it is
// never visible to anything running on the frontend's origin, including this app's own
// middleware. This is a separate, non-HttpOnly, non-sensitive cookie set on the frontend's
// own domain purely so middleware.ts can decide whether to bounce to /login before a page
// render. It carries no token value and proves nothing on its own; the API still enforces
// real authorization on every request via the JWT.
const HINT_COOKIE = "has_session";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // matches SIMPLE_JWT.REFRESH_TOKEN_LIFETIME

export function setSessionHint() {
  document.cookie = `${HINT_COOKIE}=1; path=/; max-age=${MAX_AGE_SECONDS}; samesite=lax`;
}

export function clearSessionHint() {
  document.cookie = `${HINT_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
