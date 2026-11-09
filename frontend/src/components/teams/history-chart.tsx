"use client";

import { useMemo, useState } from "react";

import { EChart, type EChartOption } from "@/components/charts/echart";
import { type Palette, readPalette } from "@/components/charts/palette";
import type { TeamSeason } from "@/lib/api/client";
import { ordinal, percent } from "@/lib/format";
import { record, signed } from "@/lib/teams";
import { currentTheme, useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export const HISTORY_METRICS = [
  {
    key: "win_pct",
    label: "Win %",
    format: (v: number) => percent(v, 0),
    // .500 is the line between a winning and a losing season
    reference: 0.5,
  },
  {
    key: "point_diff_pg",
    label: "Point differential",
    format: (v: number) => signed(v),
    reference: 0,
  },
] as const satisfies readonly {
  key: keyof TeamSeason;
  label: string;
  format: (v: number) => string;
  reference: number;
}[];

export type HistoryMetric = (typeof HISTORY_METRICS)[number];

/** "2003-04" -> "’04" */
function shortSeason(season: string): string {
  return `’${season.slice(5)}`;
}

export function buildHistoryOption(seasons: TeamSeason[], metric: HistoryMetric, palette: Palette): EChartOption {
  return {
    animationDuration: 500,
    textStyle: { fontFamily: palette.font },
    grid: { left: 4, right: 4, top: 16, bottom: 4, containLabel: true },
    tooltip: {
      trigger: "item",
      backgroundColor: palette.popover,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: { dataIndex: number }) => {
        const s = seasons[params.dataIndex];
        const title = s.is_champion ? " · <b>Champions</b>" : "";
        const note = s.in_progress ? " · <i>so far</i>" : "";
        return (
          `<b>${s.season}</b> (${s.team_abbr_then})${title}${note}<br/>` +
          `${record(s.wins, s.losses)}, ${ordinal(s.conference_rank)} in the ${s.conference}<br/>` +
          `${metric.label}: ${metric.format(s[metric.key])}`
        );
      },
    },
    xAxis: {
      type: "category",
      data: seasons.map((s) => (s.in_progress ? `${shortSeason(s.season)}*` : shortSeason(s.season))),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: palette.subtle, hideOverlap: true },
    },
    yAxis: {
      type: "value",
      splitNumber: 4,
      // Win % on quarters, so .500 sits on a gridline
      ...(metric.key === "win_pct" ? { min: 0, max: 1, interval: 0.25 } : {}),
      axisLabel: { color: palette.subtle, formatter: (v: number) => metric.format(v) },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 28,
        data: seasons.map((s) => ({
          value: s[metric.key],
          // The season in progress is an outline: it isn't finished.
          itemStyle: s.in_progress
            ? { color: "transparent", borderColor: palette.subtle, borderWidth: 1.5, borderType: "dashed" }
            : { color: s.is_champion ? palette.brand : palette.muted },
        })),
        markLine: {
          silent: true,
          symbol: "none",
          label: { show: false },
          lineStyle: { color: palette.text, opacity: 0.5, type: "solid", width: 1 },
          data: [{ yAxis: metric.reference }],
        },
      },
    ],
  };
}

/** One bar per season since the start of the data; championship seasons in orange. */
export function HistoryChart({ name, seasons }: { name: string; seasons: TeamSeason[] }) {
  const theme = useTheme();
  const [metric, setMetric] = useState<HistoryMetric>(HISTORY_METRICS[0]);
  // Colours come from CSS variables, so nothing is drawn until the real theme is known.
  const option = useMemo(
    () => (currentTheme() === theme ? buildHistoryOption(seasons, metric, readPalette(theme)) : null),
    [seasons, metric, theme],
  );
  const titles = seasons.filter((s) => s.is_champion).map((s) => s.season);
  const current = seasons.find((s) => s.in_progress);
  const label =
    `${name}: ${metric.label.toLowerCase()} by season, ${seasons[0].season} to ${seasons.at(-1)!.season}.` +
    (titles.length ? ` Champions in ${titles.join(", ")}.` : "");

  return (
    <div>
      <div role="group" aria-label="Stat shown in the chart" className="mb-4 flex flex-wrap gap-1.5">
        {HISTORY_METRICS.map((m) => (
          <button
            key={m.key}
            type="button"
            aria-pressed={m.key === metric.key}
            onClick={() => setMetric(m)}
            className={cn(
              "eyebrow h-8 border px-3 transition-colors",
              m.key === metric.key
                ? "border-foreground bg-foreground text-background"
                : "text-muted-foreground hover:border-foreground/50 hover:text-foreground",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>
      <EChart option={option} height={260} label={label} />
      <p className="mt-2 text-sm text-muted-foreground">
        {metric.key === "win_pct" ? "The line is .500: above it, a winning season. " : "Points scored minus points allowed, per game. "}
        {titles.length > 0 && (
          <>
            Championship {titles.length === 1 ? "season" : "seasons"} in <span className="font-medium text-brand">orange</span>.{" "}
          </>
        )}
        {current && <>* {current.season} so far, drawn as an outline.</>}
      </p>
    </div>
  );
}
