"use client";

import { useSyncExternalStore } from "react";

export type Theme = "dark" | "light";
const STORAGE_KEY = "theme";

/**
 * Runs before the page paints (inlined in the root layout) so there is no flash of the wrong theme.
 * Dark is the default; a saved choice wins.
 */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${STORAGE_KEY}");var d=t!=="light";var e=document.documentElement;e.classList.toggle("dark",d);e.style.colorScheme=d?"dark":"light"}catch(_){}})()`;

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage can be blocked (private mode); the theme still applies for this page view.
  }
}

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

/** The theme applied to the page right now; `null` on the server. */
export function currentTheme(): Theme | null {
  if (typeof document === "undefined") return null;
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

/** The current theme, re-rendering when it changes. Assumes dark during server rendering and hydration. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, () => currentTheme() ?? "dark", () => "dark");
}
