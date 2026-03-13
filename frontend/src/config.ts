/**
 * App branding: name and logo path.
 * - Logo: place your logo in the frontend/public folder (e.g. logo.png) and it will be served at /logo.png.
 * - Override via env: VITE_APP_NAME, VITE_APP_LOGO (path from public root, e.g. /logo.png).
 */
const env = import.meta.env;

export const APP_NAME =
  typeof env.VITE_APP_NAME === "string" && env.VITE_APP_NAME.trim()
    ? env.VITE_APP_NAME.trim()
    : "AgencyOps";

export const APP_LOGO =
  typeof env.VITE_APP_LOGO === "string" && env.VITE_APP_LOGO.trim()
    ? env.VITE_APP_LOGO.trim()
    : "/logo.svg";

/** Use relative path when loaded via file:// (Electron) so the logo resolves from dist/. */
export function getLogoUrl(): string {
  if (typeof window !== "undefined" && window.location?.protocol === "file:")
    return "./logo.svg";
  return APP_LOGO;
}

/** Frontend app version; used when checking for updates (compare with server). */
export const APP_VERSION =
  typeof env.VITE_APP_VERSION === "string" && env.VITE_APP_VERSION.trim()
    ? env.VITE_APP_VERSION.trim()
    : "0.0.1";
