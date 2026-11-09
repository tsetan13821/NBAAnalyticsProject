import Link from "next/link";

import type { MetricKey, PlayerComparison } from "@/lib/api/client";
import { type CompareState, compareHref, formatMetric, METRIC_GROUPS, type PeerGroup } from "@/lib/compare";
import { initials, ordinal, shortName } from "@/lib/format";
import { cn } from "@/lib/utils";

const PEER_NAMES: Record<string, string> = { G: "guards", F: "forwards", C: "centers" };

/**
 * Every metric, grouped, with a column per player: the value, and a bar for where it ranked that
 * season (its percentile). The best value in each row is bold.
 */
export function ComparisonTable({
  comparison,
  colors,
  leaders,
}: {
  comparison: PlayerComparison;
  colors: readonly string[];
  leaders: Map<MetricKey, number[]>;
}) {
  const metrics = new Map(comparison.metrics.map((m) => [m.key, m]));
  const players = comparison.players;

  return (
    <div className="flex flex-col gap-10">
      {METRIC_GROUPS.map((group) => (
        <table key={group.title} className="w-full table-fixed border-collapse">
          <caption className="mb-1 text-left">
            <span className="block font-display text-2xl font-bold tracking-tight uppercase">{group.title}</span>
            <span className="block text-sm text-muted-foreground">{group.note}</span>
          </caption>
          <colgroup>
            <col className="w-[6.5rem] sm:w-[13rem]" />
            {players.map((p) => (
              <col key={p.player.id} />
            ))}
          </colgroup>
          <thead>
            <tr className="border-b-2 border-foreground">
              <th scope="col" className="sr-only">
                Stat
              </th>
              {players.map((p, i) => (
                <th key={p.player.id} scope="col" className="px-1.5 py-2 text-left align-bottom sm:px-3">
                  <span className="flex min-w-0 items-center gap-1.5 text-xs font-semibold sm:text-sm">
                    <span className="size-2.5 shrink-0" style={{ backgroundColor: colors[i] }} aria-hidden="true" />
                    <span className="truncate" title={p.player.name}>
                      {/* Initials on phones, where four columns leave no room for names. */}
                      <span className="sm:hidden" aria-hidden="true">
                        {initials(p.player.name)}
                      </span>
                      <span className="max-sm:sr-only">{shortName(p.player.name)}</span>
                    </span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.keys.map((key) => {
              const metric = metrics.get(key);
              if (!metric) return null;
              const leading = leaders.get(key) ?? [];
              return (
                <tr key={key} className="border-b">
                  <th scope="row" className="py-2.5 pr-2 text-left align-top text-xs font-medium sm:text-sm">
                    {metric.label}
                    {!metric.higher_is_better && (
                      <span className="block text-[11px] font-normal text-muted-foreground">Lower is better</span>
                    )}
                  </th>
                  {players.map((p, i) => {
                    const value = p.stats[key];
                    const pct = p.percentiles[key];
                    const leads = leading.includes(p.player.id);
                    return (
                      <td key={p.player.id} className="px-1.5 py-2.5 align-top sm:px-3">
                        <span className="flex items-baseline justify-between gap-1">
                          <span
                            className={cn(
                              "tabular text-sm sm:text-base",
                              leads ? "font-bold text-foreground" : "text-muted-foreground",
                            )}
                          >
                            {formatMetric(metric, value)}
                            {leads && <span className="sr-only"> (best)</span>}
                          </span>
                          <span className="tabular text-[11px] text-muted-foreground" title={`${ordinal(Math.round(pct))} percentile`}>
                            {/* Phones show the bar alone: the number doesn't fit beside the value. */}
                            <span className="hidden sm:inline" aria-hidden="true">
                              {Math.round(pct)}
                            </span>
                            <span className="sr-only">{ordinal(Math.round(pct))} percentile</span>
                          </span>
                        </span>
                        <span className="mt-1.5 block h-1.5 bg-muted" aria-hidden="true">
                          <span
                            className={cn("block h-full", !leads && "opacity-70")}
                            style={{ width: `${Math.max(pct, 1)}%`, backgroundColor: colors[i] }}
                          />
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      ))}
    </div>
  );
}

/** Who the percentiles are measured against, for the note under the controls. */
export function peerDescription(comparison: PlayerComparison): string {
  if (comparison.peer_group === "ALL") return "every player";
  const groups = [...new Set(comparison.players.map((p) => PEER_NAMES[p.peer_group] ?? p.peer_group))];
  return groups.length === 1 ? `other ${groups[0]}` : `players at the same position (${groups.join(", ")})`;
}

/** "All players" / "Same position": links, so the choice is part of the URL. */
export function PeerToggle({ state }: { state: CompareState & { season: string } }) {
  const options: { value: PeerGroup; label: string }[] = [
    { value: "ALL", label: "All players" },
    { value: "POSITION", label: "Same position" },
  ];
  return (
    <div role="group" aria-label="Percentiles measured against" className="flex">
      {options.map(({ value, label }) => {
        const active = state.peers === value;
        return (
          <Link
            key={value}
            href={compareHref({ ...state, peers: value, q: undefined })}
            scroll={false}
            aria-current={active ? "true" : undefined}
            className={cn(
              "eyebrow inline-flex h-9 items-center border px-3 transition-colors not-first:-ml-px",
              active
                ? "relative z-10 border-foreground bg-foreground text-background"
                : "text-muted-foreground hover:border-foreground/50 hover:text-foreground",
            )}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}
