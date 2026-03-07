const STORAGE_KEY = "theme";

export type ThemeValue = "light" | "dark" | "system";

function getSystemDark(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme(): ThemeValue {
  if (typeof window === "undefined") return "light";
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "dark" || v === "light" || v === "system") return v;
  return "light";
}

export function getEffectiveTheme(): "light" | "dark" {
  const stored = getStoredTheme();
  if (stored === "dark") return "dark";
  if (stored === "light") return "light";
  return getSystemDark() ? "dark" : "light";
}

export function applyTheme(value: ThemeValue): void {
  const effective = value === "system" ? (getSystemDark() ? "dark" : "light") : value;
  const root = document.documentElement;
  const isDark = effective === "dark";
  // Tailwind darkMode: "class" — .dark on an ancestor toggles dark: variants
  if (isDark) {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  // So browser chrome (scrollbars, form controls) and meta theme-color match
  root.style.colorScheme = isDark ? "dark" : "light";
  // Force repaint so theme change is visible immediately
  void root.offsetHeight;
}

export function setTheme(value: ThemeValue): void {
  localStorage.setItem(STORAGE_KEY, value);
  applyTheme(value);
}
