import { cssColor } from "@/components/charts/echart";
import type { Theme } from "@/lib/theme";

/** Chart colours and font, resolved from the site's CSS variables. */
export type Palette = {
  brand: string;
  muted: string;
  text: string;
  subtle: string;
  grid: string;
  popover: string;
  font?: string;
};

const palettes: Partial<Record<Theme, Palette>> = {};

/** The chart palette for a theme, read from CSS variables once per theme. Call only while that theme is active. */
export function readPalette(theme: Theme): Palette {
  return (palettes[theme] ??= {
    brand: cssColor("--brand"),
    muted: cssColor("--chart-muted"),
    text: cssColor("--foreground"),
    subtle: cssColor("--muted-foreground"),
    grid: cssColor("--border"),
    popover: cssColor("--popover"),
    // next/font exposes the generated family list (with its metric-matched fallback) as a variable.
    font: getComputedStyle(document.documentElement).getPropertyValue("--font-barlow").trim() || undefined,
  });
}
