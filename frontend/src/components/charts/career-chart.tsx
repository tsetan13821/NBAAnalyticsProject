"use client";

import { useMemo, useState } from "react";

import { EChart, type EChartOption } from "@/components/charts/echart";
import { type Palette, readPalette } from "@/components/charts/palette";
import type { PlayerSeason } from "@/lib/api/client";
import { percent, shortDate, stat } from "@/lib/format";
import { currentTheme, useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export const CAREER_METRICS = [
  { key: "pts_pg", label: "Points", unit: "per game", format: (v: number) => stat(v) },
  { key: "reb_pg", label: "Rebounds", unit: "per game", format: (v: number) => stat(v) },
  { key: "ast_pg", label: "Assists", unit: "per game", format: (v: number) => stat(v) },
  { key: "ts_pct", label: "True shooting", unit: "", format: (v: number) => percent(v) },
  { key: "usg_pct", label: "Usage", unit: "", format: (v: number) => percent(v) },
  { key: "pie", label: "PIE", unit: "", format: (v: number) => percent(v) },
] as const satisfies readonly {
  key: keyof PlayerSeason;
  label: string;
  unit: string;
  format: (v: number) => string;
}[];

export type CareerMetric = (typeof CAREER_METRICS)[number];

/** "2003-04" -> "’04" (the year the season ends, as on a jersey patch) */
function shortSeason(season: string): string {
  return `’${season.slice(5)}`;
}

export function buildCareerOption(
  seasons: PlayerSeason[],
  mvpSeasons: string[],
  metric: CareerMetric,
  palette: Palette,
): EChartOption {
  const mvp = new Set(mvpSeasons);
  return {
    animationDuration: 500,
    textStyle: { fontFamily: palette.font },
    grid: { left: 4, right: 4, top: 24, bottom: 4, containLabel: true },
    tooltip: {
      trigger: "item",
      backgroundColor: palette.popover,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: { dataIndex: number }) => {
        const s = seasons[params.dataIndex];
        const award = mvp.has(s.season) ? " · <b>MVP</b>" : "";
        const note = s.in_progress ? " · <i>so far</i>" : "";
        return `<b>${s.season}</b> (${s.team_abbr_then})${award}${note}<br/>${metric.label}: ${metric.format(s[metric.key])}<br/>${s.games} games`;
      },
    },
    xAxis: {
      type: "category",
      data: seasons.map((s) => (s.in_progress ? `${shortSeason(s.season)}*` : shortSeason(s.season))),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: palette.grid } },
      axisLabel: { color: palette.subtle, hideOverlap: true },
    },
    yAxis: {
      type: "value",
      splitNumber: 4,
      axisLabel: { color: palette.subtle, formatter: (v: number) => metric.format(v).replace(/\.0(?=%|$)/, "") },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 36,
        data: seasons.map((s) => ({
          value: s[metric.key],
          // The season in progress is an outline, not a solid bar: it isn't finished.
          itemStyle: s.in_progress
            ? { color: "transparent", borderColor: palette.subtle, borderWidth: 1.5, borderType: "dashed", borderRadius: [3, 3, 0, 0] }
            : { color: mvp.has(s.season) ? palette.brand : palette.muted, borderRadius: [3, 3, 0, 0] },
        })),
        label: {
          show: seasons.length <= 14,
          position: "top",
          color: palette.subtle,
          fontSize: 11,
          formatter: (p: { value: number }) => metric.format(p.value),
        },
      },
    ],
  };
}

/** One bar per season for the chosen stat; MVP seasons are highlighted. */
export function CareerChart({
  name,
  seasons,
  mvpSeasons,
  asOf,
}: {
  name: string;
  /** Oldest first */
  seasons: PlayerSeason[];
  mvpSeasons: string[];
  /** When the season-in-progress numbers were fetched. */
  asOf?: string | null;
}) {
  const theme = useTheme();
  const [metric, setMetric] = useState<CareerMetric>(CAREER_METRICS[0]);
  // As in the MVP race chart: colours come from CSS variables, so nothing is drawn until the real theme is known.
  const option = useMemo(
    () => (currentTheme() === theme ? buildCareerOption(seasons, mvpSeasons, metric, readPalette(theme)) : null),
    [seasons, mvpSeasons, metric, theme],
  );

  // A hot start in the season under way doesn't count as a best season.
  // A player whose only season is the one under way has no best season yet.
  const finished = seasons.filter((s) => !s.in_progress);
  const best = finished.length
    ? finished.reduce((top, s) => (s[metric.key] > top[metric.key] ? s : top))
    : undefined;
  const current = seasons.find((s) => s.in_progress);
  const label =
    `${name}: ${metric.label.toLowerCase()} by season, ${seasons[0].season} to ${seasons.at(-1)!.season}.` +
    (best ? ` Best: ${metric.format(best[metric.key])} in ${best.season}.` : "");

  return (
    <div>
      <div role="group" aria-label="Stat shown in the chart" className="mb-4 flex flex-wrap gap-1.5">
        {CAREER_METRICS.map((m) => (
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
      <EChart option={option} height={300} label={label} />
      <p className="mt-2 text-sm text-muted-foreground">
        {best && (
          <>
            Best season: <span className="tabular font-medium text-foreground">{metric.format(best[metric.key])}</span>{" "}
            {metric.unit && `${metric.unit} `}in {best.season}.{" "}
          </>
        )}
        {mvpSeasons.length > 0 && <>MVP seasons are in <span className="font-medium text-brand">orange</span>. </>}
        {current && (
          <>
            * {current.season} so far ({current.games} {current.games === 1 ? "game" : "games"}
            {asOf && `, as of ${shortDate(asOf)}`}), drawn as an outline.
          </>
        )}
      </p>
    </div>
  );
}
