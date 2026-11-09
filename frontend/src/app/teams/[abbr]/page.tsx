import { ArrowLeftIcon, ArrowRightIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { GameCard } from "@/components/games/game-parts";
import { SeasonPicker } from "@/components/season-picker";
import { HistoryChart } from "@/components/teams/history-chart";
import {
  FranchiseSeasons,
  LeaderStatLinks,
  LeadersTable,
  TeamHero,
  TeamRoster,
} from "@/components/teams/team-parts";
import { Skeleton } from "@/components/ui/skeleton";
import { getGameResults, getLeaders, getRoster, getTeam, getUpcomingGames, type TeamDetail } from "@/lib/api/client";
import { ordinal, ratio } from "@/lib/format";
import { bestSeason, parseTeamAbbr, parseTeamQuery, record, signed, type TeamQuery, teamQueryHref } from "@/lib/teams";

const NEXT_GAMES = 3;
const LATEST_RESULTS = 3;

export async function generateMetadata({ params }: PageProps<"/teams/[abbr]">): Promise<Metadata> {
  const abbr = parseTeamAbbr((await params).abbr);
  const team = abbr ? await getTeam(abbr) : null;
  if (!team) return { title: "Team not found" };
  return {
    title: team.name,
    description: `${team.name}: this season's games, every season since ${team.first_season}, rosters, titles and the franchise's career leaders.`,
  };
}

export default function TeamPage({ params, searchParams }: PageProps<"/teams/[abbr]">) {
  return (
    <>
      <div className="mb-6">
        <Link href="/teams" className="eyebrow inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
          <ArrowLeftIcon className="size-3.5" />
          All franchises
        </Link>
      </div>
      <Suspense fallback={<FranchiseSkeleton />}>
        <Franchise params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Franchise({ params, searchParams }: Pick<PageProps<"/teams/[abbr]">, "params" | "searchParams">) {
  const abbr = parseTeamAbbr((await params).abbr);
  if (!abbr) notFound();
  const team = await getTeam(abbr);
  if (!team) notFound();
  const query = parseTeamQuery(await searchParams);
  const { latest } = team;
  const best = bestSeason(team.seasons);

  return (
    <>
      <TeamHero team={team} />

      <FigureRow>
        <Figure
          label={latest.in_progress ? `${latest.season} so far` : latest.season}
          value={record(latest.wins, latest.losses)}
          detail={`${ordinal(latest.conference_rank)} in the ${team.conference}`}
          tone="brand"
        />
        <Figure
          label="Point differential"
          value={signed(latest.point_diff_pg)}
          detail={latest.in_progress ? "Per game, this season" : `Per game, ${latest.season}`}
        />
        <Figure
          label={`Titles since ${team.first_season}`}
          value={team.titles}
          detail={team.championships.length ? team.championships.join(", ") : "None in this span"}
        />
        {best && <Figure label="Best season" value={record(best.wins, best.losses)} detail={best.season} />}
      </FigureRow>

      <Suspense fallback={<Skeleton className="mt-16 h-72 w-full" />}>
        <ThisSeason team={team} />
      </Suspense>

      <Section>
        <SectionHeading number="02" title="Season by season" aside={`${team.seasons.length} seasons since ${team.first_season}`} />
        <HistoryChart name={team.name} seasons={team.seasons} />
        <div className="mt-10">
          <FranchiseSeasons team={team} query={query} />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Open a season to see its roster. Relocated franchises keep their history: the abbreviation of the time is in
          the second column.
        </p>
      </Section>

      <Suspense fallback={<Skeleton className="mt-16 h-96 w-full" />}>
        <RosterSection team={team} query={query} />
      </Suspense>

      <Suspense fallback={<Skeleton className="mt-16 h-96 w-full" />}>
        <LeadersSection team={team} query={query} />
      </Suspense>
    </>
  );
}

/** The game predictor on this team: the next games and the latest results, as predicted before tip-off. */
async function ThisSeason({ team }: { team: TeamDetail }) {
  const [upcoming, results] = await Promise.all([getUpcomingGames(team.abbr), getGameResults(LATEST_RESULTS, 0, team.abbr)]);
  const { record: track } = results;
  if (upcoming.games.length === 0 && track.games === 0) return null;
  return (
    <Section>
      <SectionHeading
        number="01"
        title={`${track.season ?? upcoming.season} games`}
        aside={
          track.games > 0 && (
            <Link href={`/games/results?team=${team.abbr}`} className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
              Every result <ArrowRightIcon className="size-3.5" />
            </Link>
          )
        }
      />
      <div className="grid gap-10 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-display text-xl font-bold uppercase">Next up</h3>
          {upcoming.games.length ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {upcoming.games.slice(0, NEXT_GAMES).map((game) => (
                <GameCard key={game.game_id} game={game} />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No games in the next seven days.</p>
          )}
        </div>
        <div>
          <h3 className="mb-3 font-display text-xl font-bold uppercase">Latest results</h3>
          {track.games ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                {results.items.map((game) => (
                  <GameCard key={game.game_id} game={game} />
                ))}
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                The game predictor has called the winner of{" "}
                <span className="tabular font-medium text-foreground">{ratio(track.correct, track.games)}</span>{" "}
                {team.nickname} games this season, each before tip-off.
              </p>
            </>
          ) : (
            <p className="text-muted-foreground">No games played yet.</p>
          )}
        </div>
      </div>
    </Section>
  );
}

async function RosterSection({ team, query }: { team: TeamDetail; query: TeamQuery }) {
  const seasons = team.seasons.map((s) => s.season);
  const season = query.season && seasons.includes(query.season) ? query.season : seasons.at(-1)!;
  const roster = await getRoster(team.abbr, season);
  const inProgress = team.seasons.find((s) => s.season === season)?.in_progress;
  return (
    <Section>
      <SectionHeading
        number="03"
        id="roster"
        title="Roster"
        aside={
          <SeasonPicker
            seasons={seasons}
            current={season}
            href={teamQueryHref(team.abbr, { ...query, season: "{season}" }, "roster")}
            scroll={false}
          />
        }
      />
      {roster ? (
        <TeamRoster roster={roster} inProgress={inProgress} />
      ) : (
        <p className="border-y py-6 text-muted-foreground">No player stats for {team.name} in {season}.</p>
      )}
      <p className="mt-4 text-sm text-muted-foreground">
        Per-game averages, top scorers first.{" "}
        {inProgress
          ? "The season under way lists everyone who has played so far."
          : "Completed seasons list players with at least 20 games."}{" "}
        A player traded during a season is listed with the team he finished it with.
      </p>
    </Section>
  );
}

async function LeadersSection({ team, query }: { team: TeamDetail; query: TeamQuery }) {
  const leaders = await getLeaders(team.abbr, query.by);
  if (!leaders || leaders.leaders.length === 0) return null;
  return (
    <Section>
      <SectionHeading number="04" id="leaders" title="Franchise leaders" aside={`Totals since ${leaders.since}`} />
      <LeaderStatLinks abbr={team.abbr} query={query} />
      <LeadersTable leaders={leaders} />
      <p className="mt-4 text-sm text-muted-foreground">
        Career totals with the {team.nickname} from {leaders.since} on, the first season in this data, so careers that
        began earlier count only their later years. Seasons of fewer than 20 games aren&apos;t in the data, and a player
        traded during a season counts entirely for the team he finished it with.
      </p>
    </Section>
  );
}

function FranchiseSkeleton() {
  return (
    <>
      <Skeleton className="mb-10 h-56 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="mt-16 h-72 w-full" />
    </>
  );
}
