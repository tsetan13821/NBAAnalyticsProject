"use client";

import { useMemo } from "react";

import { cssColor, EChart, type EChartOption } from "@/components/charts/echart";
import type { MvpCandidate } from "@/lib/api/client";
import { percent, shortName } from "@/lib/format";
import { currentTheme, type Theme, useTheme } from "@/lib/theme";

const BAR_HEIGHT = 34;

type Palette = { brand: string; muted: string; text: string; subtle: string; grid: string; popover: string };

const palettes: Partial<Record<Theme, Palette>> = {};

/** The chart colours for a theme, read from CSS variables once per theme. Call only while that theme is active. */
function readPalette(theme: Theme): Palette {
  return (palettes[theme] ??= {
    brand: cssColor("--brand"),
    muted: cssColor("--chart-muted"),
    text: cssColor("--foreground"),
    subtle: cssColor("--muted-foreground"),
    grid: cssColor("--border"),
    popover: cssColor("--popover"),
  });
}

export function buildRaceOption(candidates: MvpCandidate[], palette: Palette): EChartOption {
  return {
    animationDuration: 600,
    grid: { left: 8, right: 56, top: 8, bottom: 24, containLabel: true },
    tooltip: {
      trigger: "item",
      backgroundColor: palette.popover,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: { dataIndex: number }) => {
        const c = candidates[params.dataIndex];
        const mvp = c.is_mvp ? " · <b>MVP</b>" : "";
        return `<b>${c.player.name}</b> (${c.team.abbr})${mvp}<br/>Share of model score: ${percent(c.score_share)}`;
      },
    },
    xAxis: {
      type: "value",
      splitNumber: 4,
      axisLabel: { color: palette.subtle, hideOverlap: true, formatter: (v: number) => percent(v, 0) },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: candidates.map((c) => shortName(c.player.name)),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: palette.text, fontSize: 12 },
    },
    series: [
      {
        type: "bar",
        barWidth: BAR_HEIGHT * 0.55,
        data: candidates.map((c) => ({
          value: c.score_share,
          itemStyle: { color: c.is_mvp ? palette.brand : palette.muted, borderRadius: [0, 4, 4, 0] },
        })),
        label: {
          show: true,
          position: "right",
          color: palette.subtle,
          formatter: (p: { value: number }) => percent(p.value),
        },
      },
    ],
  };
}

/** Horizontal bars of each candidate's share of the model's score; the real MVP is highlighted. */
export function MvpRaceChart({ season, candidates }: { season: string; candidates: MvpCandidate[] }) {
  const theme = useTheme();
  // Colours come from CSS variables, so rebuild the option whenever the theme changes. Nothing is drawn
  // on the server, or during hydration while `theme` is still the server's guess rather than the real one.
  const option = useMemo(
    () => (currentTheme() === theme ? buildRaceOption(candidates, readPalette(theme)) : null),
    [candidates, theme],
  );

  const height = candidates.length * BAR_HEIGHT + 40;
  const mvp = candidates.find((c) => c.is_mvp);
  const label =
    `${season} MVP race: share of the model's score for ${candidates.length} candidates.` +
    (mvp ? ` The real MVP, ${mvp.player.name}, ranked ${mvp.rank}.` : "");
  return <EChart option={option} height={height} label={label} />;
}
