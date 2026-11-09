import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { PlayerResults } from "@/components/players/player-results";
import { PlayerSearchForm } from "@/components/players/player-search-form";
import { Skeleton } from "@/components/ui/skeleton";
import { getMeta, getTeams, searchPlayers } from "@/lib/api/client";
import { seasonsBetween } from "@/lib/format";
import { parsePlayerFilters, type PlayerFilters, playersHref, toPlayerQuery } from "@/lib/player-search";

export const metadata: Metadata = {
  title: "Players",
  description: "Search every NBA player since 2000-01 by name, position, team and season.",
};

export default function PlayersPage({ searchParams }: PageProps<"/players">) {
  return (
    <>
      <PageHeader
        eyebrow="Every player since 2000-01"
        title="Players"
        lede="Search by name, or narrow the list by position, team and season. Each profile has the player's season-by-season numbers and the players whose game was most like theirs."
      />
      <Suspense fallback={<SearchSkeleton />}>
        <Search searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Search({ searchParams }: Pick<PageProps<"/players">, "searchParams">) {
  const filters = parsePlayerFilters(await searchParams);
  const [teams, meta] = await Promise.all([getTeams(), getMeta()]);
  return (
    <>
      <PlayerSearchForm
        filters={filters}
        teams={teams.toSorted((a, b) => a.name.localeCompare(b.name))}
        seasons={seasonsBetween(meta.first_season, meta.current_season ?? meta.last_season).toReversed()}
        currentSeason={meta.current_season ?? undefined}
      />
      {/* A new key per search, so a new search shows the skeleton instead of the previous results. */}
      <Suspense key={playersHref(filters)} fallback={<ResultsSkeleton />}>
        <Results filters={filters} />
      </Suspense>
    </>
  );
}

async function Results({ filters }: { filters: PlayerFilters }) {
  const page = await searchPlayers(toPlayerQuery(filters));
  return <PlayerResults page={page} filters={filters} />;
}

function SearchSkeleton() {
  return (
    <>
      <Skeleton className="mb-4 h-14 w-full" />
      <Skeleton className="mb-10 h-14 w-full max-w-xl" />
      <ResultsSkeleton />
    </>
  );
}

function ResultsSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="mb-2 h-8 w-64" />
      {Array.from({ length: 8 }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
