import { ArrowLeftIcon, ColumnsIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { CareerChart } from "@/components/charts/career-chart";
import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { PlayerHero } from "@/components/players/player-hero";
import { SeasonTable } from "@/components/players/season-table";
import { SimilarPlayers } from "@/components/players/similar-players";
import { SeasonPicker } from "@/components/season-picker";
import { Skeleton } from "@/components/ui/skeleton";
import { compareHref } from "@/lib/compare";
import { getMeta, getPlayer, getSimilarPlayers, type PlayerProfile } from "@/lib/api/client";
import { isSeason, stat } from "@/lib/format";
import { parsePlayerId } from "@/lib/player-search";

export async function generateMetadata({ params }: PageProps<"/players/[id]">): Promise<Metadata> {
  const id = parsePlayerId((await params).id);
  const profile = id ? await getPlayer(id) : null;
  if (!profile) return { title: "Player not found" };
  return {
    title: profile.name,
    description: `${profile.name}: season-by-season stats, career averages and the most similar players, ${profile.first_season} to ${profile.last_season}.`,
  };
}

export default function PlayerPage({ params, searchParams }: PageProps<"/players/[id]">) {
  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-4">
        <Link href="/players" className="eyebrow inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
          <ArrowLeftIcon className="size-3.5" />
          All players
        </Link>
        <Suspense>
          <CompareLink params={params} />
        </Suspense>
      </div>
      <Suspense fallback={<ProfileSkeleton />}>
        <Profile params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Profile({ params, searchParams }: Pick<PageProps<"/players/[id]">, "params" | "searchParams">) {
  const id = parsePlayerId((await params).id);
  if (!id) notFound();
  const [profile, meta] = await Promise.all([getPlayer(id), getMeta()]);
  if (!profile) notFound();

  return (
    <>
      <PlayerHero profile={profile} rostersAsOf={meta.rosters_as_of} />

      <FigureRow>
        <Figure label="Points per game" value={stat(profile.career.pts_pg)} tone="brand" />
        <Figure label="Rebounds" value={stat(profile.career.reb_pg)} />
        <Figure label="Assists" value={stat(profile.career.ast_pg)} />
        <Figure label="Games" value={profile.career.games.toLocaleString("en-US")} detail="Regular season" />
      </FigureRow>

      <Section className="mt-16">
        <SectionHeading number="01" title="Career arc" />
        <CareerChart
          name={profile.name}
          seasons={profile.seasons}
          mvpSeasons={profile.mvp_seasons}
          asOf={meta.current_season_as_of}
        />
      </Section>

      <Section>
        <SectionHeading number="02" title="Season by season" aside="Bold: best completed season in that column" />
        <SeasonTable profile={profile} asOf={meta.current_season_as_of} />
      </Section>

      <Suspense fallback={<Skeleton className="mt-16 h-80 w-full" />}>
        <Similar profile={profile} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Similar({
  profile,
  searchParams,
}: {
  profile: PlayerProfile;
  searchParams: PageProps<"/players/[id]">["searchParams"];
}) {
  // Only seasons with enough playing time get a role, and similarity is measured between roles.
  const seasons = profile.seasons.filter((s) => s.archetype).map((s) => s.season);
  const requested = (await searchParams).season;
  const season = typeof requested === "string" && isSeason(requested) && seasons.includes(requested) ? requested : seasons.at(-1);
  const data = season ? await getSimilarPlayers(profile.id, season) : null;

  return (
    <Section>
      <SectionHeading
        number="03"
        title="Most similar players"
        aside={
          data &&
          seasons.length > 1 && (
            <SeasonPicker seasons={seasons} current={data.season} href={`/players/${profile.id}?season={season}`} scroll={false} />
          )
        }
      />
      {data ? (
        <SimilarPlayers data={data} />
      ) : (
        <p className="border-y py-6 text-muted-foreground">
          {profile.seasons.every((s) => s.in_progress)
            ? `Roles are given once a player reaches 20 games in a season, so there are no comparisons for ${profile.name} yet.`
            : `${profile.name} never had a season with enough playing time to be given a role (at least 20 games, 15 minutes a game and 12% usage), so there are no comparisons for this player.`}
        </p>
      )}
      <details className="mt-6 border-l-[3px] border-brand bg-paper px-5 py-4 text-sm leading-relaxed text-muted-foreground">
        <summary className="eyebrow cursor-pointer text-brand">How roles and similarity work</summary>
        <p className="mt-3">
          Every player with at least 20 games, 15 minutes a game and 12% usage in a season gets four scores, each
          the average of a few standardised stats: <b className="text-foreground">scoring</b> (points, usage, true
          shooting), <b className="text-foreground">playmaking</b> (assists, assist rate),{" "}
          <b className="text-foreground">rebounding</b> (rebounds, rebound rate) and{" "}
          <b className="text-foreground">defence</b> (steals, blocks, defensive rating). The highest score is the
          player&apos;s role. Within each role, a one-dimensional k-means clustering splits players into elite, very
          good and average tiers.
        </p>
        <p className="mt-2">
          The most similar players are the five with the smallest straight-line distance between their four scores
          and this player&apos;s, in the same season. It measures how a player&apos;s game was shaped, not how good the
          player was: a role player can sit next to a star with the same mix of skills.
        </p>
      </details>
    </Section>
  );
}

async function CompareLink({ params }: Pick<PageProps<"/players/[id]">, "params">) {
  const id = parsePlayerId((await params).id);
  if (!id) return null;
  return (
    <Link
      href={compareHref({ ids: [id], peers: "ALL" })}
      className="eyebrow inline-flex items-center gap-1.5 text-muted-foreground hover:text-brand"
    >
      <ColumnsIcon className="size-3.5" />
      Compare
    </Link>
  );
}

function ProfileSkeleton() {
  return (
    <>
      <div className="mb-12 grid gap-8 md:grid-cols-[1fr_22rem] md:items-end">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-20 w-full max-w-lg" />
          <Skeleton className="mt-4 h-24 w-full" />
        </div>
        <Skeleton className="aspect-[1040/760] w-full" />
      </div>
      <Skeleton className="h-28 w-full" />
      <Skeleton className="mt-16 h-80 w-full" />
    </>
  );
}
