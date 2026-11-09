"use client";

import { BarChart } from "echarts/charts";
import { GridComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

// Register only what the app uses, so the bundle stays small.
echarts.use([BarChart, GridComponent, MarkLineComponent, TooltipComponent, SVGRenderer]);

export type EChartOption = echarts.EChartsCoreOption;

/** Minimal React wrapper: creates the chart once, updates the option, resizes with its container. */
export function EChart({
  option,
  height,
  label,
  className,
}: {
  /** `null` renders an empty placeholder of the same size (e.g. during server rendering). */
  option: EChartOption | null;
  height: number;
  /** Accessible description of what the chart shows. */
  label: string;
  className?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const instance = echarts.init(element, null, { renderer: "svg" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    if (option) chart.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div ref={container} role="img" aria-label={label} className={cn("w-full", className)} style={{ height }} />;
}

/**
 * Resolve a CSS custom property (e.g. "--brand") to an rgb() string.
 * The theme uses oklch(), which ECharts cannot parse, so the browser converts it by painting one pixel.
 */
export function cssColor(variable: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  const context = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  if (!value || !context) return "#888888";
  context.fillStyle = value;
  context.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = context.getImageData(0, 0, 1, 1).data;
  return a === 255 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(3)})`;
}
