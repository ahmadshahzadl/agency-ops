/**
 * App branding: name and logo path.
 * - Logo: place your logo in the frontend/public folder (e.g. logo.png) and it will be served at /logo.png.
 * - Override via env: VITE_APP_NAME, VITE_APP_LOGO (path from public root, e.g. /logo.png).
 */
const env = import.meta.env;

export const APP_NAME = (typeof env.VITE_APP_NAME === "string" && env.VITE_APP_NAME.trim())
  ? env.VITE_APP_NAME.trim()
  : "Software House";

export const APP_LOGO = (typeof env.VITE_APP_LOGO === "string" && env.VITE_APP_LOGO.trim())
  ? env.VITE_APP_LOGO.trim()
  : "/logo.png";
