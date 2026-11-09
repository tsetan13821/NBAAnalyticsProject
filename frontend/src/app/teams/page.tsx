import type { Metadata } from "next";
import { Suspense } from "react";

import { Section, SectionHeading } from "@/components/editorial";
import { PageHeader } from "@/components/page-header";
import { ChampionsList, StandingsTable } from "@/components/teams/team-parts";
import { Skeleton } from "@/components/ui/skeleton";
import { getMeta, getSeasons, getTeams } from "@/lib/api/client";
import { shortDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Franchises",
  description: "Standings for the season under way and every NBA champion since 2000-01, with a page for each of the 30 franchises.",
};

export default function TeamsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Franchises"
        title="All thirty teams"
        lede="This season's standings and every champion since 2000-01. Open a team for its record season by season, its rosters, and the players who did the most for it."
      />
      <Suspense fallback={<StandingsSkeleton />}>
        <Standings />
      </Suspense>
    </>
  );
}

async function Standings() {
  const [teams, meta, seasons] = await Promise.all([getTeams(), getMeta(), getSeasons()]);
  const latest = teams[0].latest;
  return (
    <>
      <Section>
        <SectionHeading
          number="01"
          title={`${latest.season} standings`}
          aside={
            latest.in_progress
              ? `So far${meta.current_season_as_of ? `, as of ${shortDate(meta.current_season_as_of)}` : ""}`
              : "Final regular-season standings"
          }
        />
        <div className="grid gap-10 lg:grid-cols-2">
          <StandingsTable teams={teams} conference="East" since={meta.first_season} />
          <StandingsTable teams={teams} conference="West" since={meta.first_season} />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Ranked by the league&apos;s own standings, tie-breakers included. +/− is points scored minus points allowed
          per game; titles count from {meta.first_season}.
        </p>
      </Section>
      <Section>
        <SectionHeading number="02" title={`Champions since ${meta.first_season}`} />
        <ChampionsList seasons={seasons} />
      </Section>
    </>
  );
}

function StandingsSkeleton() {
  return (
    <div className="grid gap-10 lg:grid-cols-2">
      <Skeleton className="h-[34rem] w-full" />
      <Skeleton className="h-[34rem] w-full" />
    </div>
  );
}
