import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import type { EraAccuracy, MvpSeasonResult, PlayerRef } from "@/lib/api/client";
import { ordinal, ratio } from "@/lib/format";
import { cn } from "@/lib/utils";

function Player({ player }: { player: PlayerRef }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <PlayerAvatar player={player} size="sm" />
      <span className="truncate font-medium">{player.name}</span>
    </span>
  );
}

/** Every season as a ledger row (newest first), grouped by era: the pick, the winner, the verdict. */
export function SeasonLedger({ results, eras }: { results: MvpSeasonResult[]; eras: EraAccuracy[] }) {
  const newestFirst = results.toReversed();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-sm">
        <thead>
          <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-semibold">Season</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Model&apos;s pick</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Actual MVP</th>
            <th scope="col" className="py-2 text-right font-semibold">Result</th>
          </tr>
        </thead>
        {eras
          .toSorted((a, b) => b.era - a.era)
          .map((era) => (
            <tbody key={era.era}>
              <tr>
                <th colSpan={4} scope="colgroup" className="pt-6 pb-2 text-left">
                  <span className="font-display text-lg font-bold tracking-tight uppercase">{era.label}</span>
                  <span className="tabular ml-3 text-muted-foreground">{ratio(era.correct, era.seasons)} correct</span>
                </th>
              </tr>
              {newestFirst
                .filter((result) => result.era === era.era)
                .map((result) => (
                  <tr key={result.season} className="group border-t transition-colors hover:bg-muted/50">
                    <td className="py-2 pr-4">
                      <Link
                        href={`/mvp/${result.season}`}
                        className="tabular font-display text-lg font-bold underline-offset-4 group-hover:text-brand group-hover:underline"
                      >
                        {result.season}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">
                      <Player player={result.predicted} />
                    </td>
                    <td className="py-2 pr-4">
                      {result.correct ? (
                        <span className="text-muted-foreground">Same</span>
                      ) : (
                        <Player player={result.actual} />
                      )}
                    </td>
                    <td className="py-2 text-right">
                      <span className={cn("eyebrow whitespace-nowrap", result.correct ? "text-hit" : "text-miss")}>
                        {result.correct ? "Hit" : `Miss · MVP ${ordinal(result.actual_rank)}`}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          ))}
      </table>
    </div>
  );
}
