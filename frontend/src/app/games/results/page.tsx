import { ArrowLeftIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { GameCard } from "@/components/games/game-parts";
import { PageHeader } from "@/components/page-header";
import { TeamBadge } from "@/components/team-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getGameResults, getTeams } from "@/lib/api/client";
import { percent, ratio } from "@/lib/format";
import { byDate, longDate } from "@/lib/games";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Game predictor results",
  description: "Every game of the NBA season so far, with the model's pre-game prediction and the final score.",
};

const PAGE_SIZE = 24;

type Query = { page: number; team?: string };

function parseQuery(params: Record<string, string | string[] | undefined>): Query {
  const page = Number([params.page].flat()[0]);
  const team = [params.team].flat()[0]?.toUpperCase();
  return { page: Number.isInteger(page) && page > 1 ? page : 1, team: team && /^[A-Z]{3}$/.test(team) ? team : undefined };
}

function href({ page, team }: Query): string {
  const parts = [team && `team=${team}`, page > 1 && `page=${page}`].filter(Boolean);
  return parts.length ? `/games/results?${parts.join("&")}` : "/games/results";
}

export default function ResultsPage({ searchParams }: PageProps<"/games/results">) {
  return (
    <>
      <Link href="/games" className="eyebrow mb-6 inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" /> Coming up
      </Link>
      <PageHeader
        eyebrow="Game predictor"
        title="Every result"
        lede="Each game of the season so far, as the model predicted it before tip-off, against the final score."
      />
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <Results searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Results({ searchParams }: Pick<PageProps<"/games/results">, "searchParams">) {
  const query = parseQuery(await searchParams);
  const [results, teams] = await Promise.all([
    getGameResults(PAGE_SIZE, (query.page - 1) * PAGE_SIZE, query.team),
    getTeams(),
  ]);
  const { record } = results;
  const pages = Math.max(1, Math.ceil(results.total / PAGE_SIZE));

  return (
    <>
      <nav aria-label="Filter by team" className="mb-8 flex flex-wrap gap-1.5">
        <Link
          href={href({ page: 1 })}
          aria-current={!query.team ? "page" : undefined}
          className={cn("eyebrow rounded border px-2 py-1", !query.team ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground")}
        >
          All teams
        </Link>
        {teams.map((team) => (
          <Link
            key={team.abbr}
            href={href({ page: 1, team: team.abbr })}
            aria-current={query.team === team.abbr ? "page" : undefined}
            className={cn("rounded p-0.5", query.team === team.abbr ? "ring-2 ring-foreground" : "opacity-70 hover:opacity-100")}
          >
            <TeamBadge team={team} />
          </Link>
        ))}
      </nav>

      <p className="mb-8 font-serif text-lg">
        {record.games === 0 ? (
          "No games played yet."
        ) : (
          <>
            <span className="tabular font-semibold">{ratio(record.correct, record.games)}</span> winners called (
            {percent(record.accuracy ?? 0)}){query.team ? ` in ${query.team} games` : ""}.
          </>
        )}
      </p>

      <div className="space-y-10">
        {byDate(results.items).map(([day, games]) => (
          <div key={day}>
            <h2 className="mb-3 font-display text-xl font-bold uppercase">{longDate(day)}</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {games.map((game) => (
                <GameCard key={game.game_id} game={game} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {pages > 1 && (
        <nav aria-label="Pages" className="mt-10 flex items-center justify-between border-t pt-4 text-sm">
          {query.page > 1 ? (
            <Link href={href({ ...query, page: query.page - 1 })} className="text-brand hover:underline">
              ← Newer
            </Link>
          ) : (
            <span />
          )}
          <span className="tabular text-muted-foreground">
            Page {query.page} of {pages}
          </span>
          {query.page < pages ? (
            <Link href={href({ ...query, page: query.page + 1 })} className="text-brand hover:underline">
              Older →
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}
    </>
  );
}
