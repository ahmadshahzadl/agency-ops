import { useState } from "react";
import { getLogoUrl } from "@/config";

const FallbackIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
  </svg>
);

interface BrandLogoProps {
  /** Sidebar: small, light icon. Login: slightly larger, can be dark. */
  variant?: "sidebar" | "login";
  className?: string;
}

export function BrandLogo({ variant = "sidebar", className = "" }: BrandLogoProps) {
  const [failed, setFailed] = useState(false);

  const size = variant === "sidebar" ? "h-16 w-auto" : "h-12 w-auto";
  const iconClass = variant === "sidebar" ? "h-16 w-16 text-white" : "h-12 w-12 text-gray-700";

  if (failed) {
    return <FallbackIcon className={`${iconClass} flex-shrink-0 ${className}`} />;
  }

  return (
    <img
      src={getLogoUrl()}
      alt=""
      className={`${size} object-contain flex-shrink-0 ${className}`}
      onError={() => setFailed(true)}
    />
  );
}
