import Link from "next/link";

import type { MvpSeasonResult } from "@/lib/api/client";
import { ordinal } from "@/lib/format";
import { cn } from "@/lib/utils";

export function describeResult(result: MvpSeasonResult): string {
  return result.correct
    ? `${result.season}: the model picked ${result.actual.name}, who won.`
    : `${result.season}: the model picked ${result.predicted.name}; ${result.actual.name} won and was the model's ${ordinal(result.actual_rank)} choice.`;
}

/**
 * Every season as one cell, oldest to newest: green when the model's pick won, red when it missed
 * (with the real MVP's rank in the model's list). A heavier line marks the switch between the two eras.
 */
export function SeasonStrip({ results, current }: { results: MvpSeasonResult[]; current?: string }) {
  return (
    <figure>
      <ol className="grid grid-cols-13 border-t border-l lg:grid-cols-26" aria-label="Model result for each season">
        {results.map((result, index) => {
          const eraStart = index > 0 && results[index - 1].era !== result.era;
          return (
            <li
              key={result.season}
              className={cn("border-r border-b", eraStart && "lg:border-l-2 lg:border-l-foreground")}
            >
              <Link
                href={`/mvp/${result.season}`}
                aria-label={describeResult(result)}
                title={describeResult(result)}
                aria-current={result.season === current ? "page" : undefined}
                className={cn(
                  "group relative flex h-20 flex-col justify-between px-1 pt-2 pb-1.5 transition-colors focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-ring",
                  result.correct ? "bg-hit/12 hover:bg-hit/25" : "bg-miss/12 hover:bg-miss/25",
                  result.season === current && "outline-2 -outline-offset-2 outline-foreground",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn("absolute inset-x-0 top-0 h-[3px]", result.correct ? "bg-hit" : "bg-miss")}
                />
                <span
                  aria-hidden="true"
                  className={cn(
                    "tabular text-center font-display text-2xl leading-none font-bold",
                    result.correct ? "text-hit" : "text-miss",
                  )}
                >
                  {result.correct ? "✓" : result.actual_rank}
                </span>
                <span aria-hidden="true" className="tabular text-center font-display text-[0.7rem] leading-none font-semibold text-muted-foreground">
                  ’{result.season.slice(5)}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      <figcaption className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="size-3 bg-hit" aria-hidden="true" /> Model&apos;s pick won
        </span>
        <span className="flex items-center gap-2">
          <span className="size-3 bg-miss" aria-hidden="true" /> Missed. The number is where the real MVP ranked
        </span>
        <span className="hidden items-center gap-2 lg:flex">
          <span className="h-3 w-0.5 bg-foreground" aria-hidden="true" /> Era change (2008-09)
        </span>
      </figcaption>
    </figure>
  );
}
