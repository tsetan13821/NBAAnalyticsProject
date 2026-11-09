import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AddPlayerForm, type Candidate, CandidateList } from "@/components/compare/add-player";
import { AddPlayerSlots } from "@/components/compare/add-player-slots";
import { CompareBar } from "@/components/compare/compare-bar";
import { ComparisonTable, PeerToggle, peerDescription } from "@/components/compare/comparison-table";
import { Lineup, type LineupEntry } from "@/components/compare/lineup";
import { Section, SectionHeading } from "@/components/editorial";
import { PageHeader } from "@/components/page-header";
import { SeasonPicker } from "@/components/season-picker";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getComparison,
  getMeta,
  getMvpRace,
  getPlayer,
  getSimilarPlayers,
  getTeams,
  type Meta,
  type PlayerProfile,
  searchPlayers,
  type TeamSummary,
} from "@/lib/api/client";
import {
  type CompareState,
  compareHref,
  leadCounts,
  MAX_PLAYERS,
  metricLeaders,
  MIN_PLAYERS,
  parseCompareState,
  PLAYER_COLORS,
  sharedSeasons,
  withoutPlayer,
  withPlayer,
} from "@/lib/compare";
import { seasonSpan, shortDate } from "@/lib/format";

const DESCRIPTION = "Put two to four NBA players side by side in one season, with where each ranked across the league.";

export async function generateMetadata({ searchParams }: PageProps<"/compare">): Promise<Metadata> {
  const { ids } = parseCompareState(await searchParams);
  const names = (await Promise.all(ids.map(getPlayer))).flatMap((p) => (p ? [p.name] : []));
  return {
    title: names.length >= MIN_PLAYERS ? names.join(" vs ") : "Compare players",
    description: DESCRIPTION,
  };
}

export default function ComparePage({ searchParams }: PageProps<"/compare">) {
  return (
    <>
      <PageHeader
        eyebrow="Head to head"
        title="Compare players"
        lede="Pick two to four players, then press Compare. Each bar shows where a player ranked in a season they all played, so a bar at 90 means better than 90% of the league."
      />
      <Suspense fallback={<CompareSkeleton />}>
        <Compare searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Compare({ searchParams }: Pick<PageProps<"/compare">, "searchParams">) {
  const requested = parseCompareState(await searchParams);
  const [meta, teams, ...found] = await Promise.all([getMeta(), getTeams(), ...requested.ids.map(getPlayer)]);
  // Unknown ids are dropped, so a stale link still shows the players that exist.
  const profiles = found.filter((p): p is PlayerProfile => p !== null);
  const shared = sharedSeasons(profiles);
  const season = requested.season && shared.includes(requested.season) ? requested.season : shared.at(-1);
  const state: CompareState = { ...requested, ids: profiles.map((p) => p.id), season };

  const ready = profiles.length >= MIN_PLAYERS && season !== undefined;
  // Fetched only once Compare has been pressed: until then the lineup is still being picked.
  const comparison = ready && state.show ? await getComparison(state.ids, season, state.peers) : null;
  const leaders = comparison ? metricLeaders(comparison) : undefined;
  const leads = leaders ? leadCounts(leaders) : undefined;
  const teamByAbbr = new Map(teams.map((t) => [t.abbr, t]));

  const entries: LineupEntry[] = profiles.map((profile, i) => {
    const played = season ? profile.seasons.find((s) => s.season === season) : undefined;
    return {
      player: profile,
      color: PLAYER_COLORS[i],
      removeHref: compareHref({ ...withoutPlayer(state, profile.id), q: undefined }),
      team: played ? teamThen(teamByAbbr, played.team_abbr, played.team_abbr_then) : (profile.current_team ?? profile.latest_team),
      games: played?.games,
      leads: leads ? (leads.get(profile.id) ?? 0) : undefined,
    };
  });

  return (
    <>
      <Lineup
        entries={entries}
        metricCount={comparison?.metrics.length}
        openSlots={
          profiles.length < MAX_PLAYERS && (
            // A new key when the lineup changes, so adding a player closes the picker.
            <AddPlayerSlots key={state.ids.join(",")} state={state}>
              <AddPlayerForm state={state} />
              {/* A new key per search, so a new search shows the skeleton instead of the previous matches. */}
              <Suspense key={state.q ?? ""} fallback={<Skeleton className="mt-3 h-40 w-full" />}>
                <Candidates state={state} profiles={profiles} meta={meta} />
              </Suspense>
            </AddPlayerSlots>
          )
        }
      />

      {profiles.length === 0 ? (
        <CompareBar count={0}>
          <Suspense fallback="Pick an open slot to add the first player.">
            <Start meta={meta} state={state} />
          </Suspense>
        </CompareBar>
      ) : profiles.length < MIN_PLAYERS ? (
        <CompareBar count={1}>Add at least one more player to compare with {profiles[0].name}.</CompareBar>
      ) : !season ? (
        <NoSharedSeason profiles={profiles} state={state} />
      ) : !state.show ? (
        <CompareBar count={profiles.length} href={`${compareHref({ ...state, q: undefined, show: true })}#head-to-head`}>
          {profiles.length < MAX_PLAYERS
            ? `Add up to ${MAX_PLAYERS - profiles.length} more, or compare these ${profiles.length} now.`
            : "The lineup is full."}{" "}
          {shared.length > 1
            ? `They played ${shared.length} seasons together; the comparison opens on ${season}.`
            : `They played one season together, ${season}.`}
        </CompareBar>
      ) : !comparison ? (
        <p className="mt-10 border-y py-6 text-muted-foreground">There are no {season} numbers for one of these players.</p>
      ) : (
        <Section className="mt-14">
          <SectionHeading
            id="head-to-head"
            number="01"
            title={`Head to head, ${season}`}
            aside={
              <div className="flex flex-wrap items-center gap-2">
                {shared.length > 1 && (
                  <SeasonPicker
                    seasons={shared}
                    current={season}
                    href={compareHref({ ...state, season: "{season}", q: undefined })}
                    scroll={false}
                  />
                )}
                <PeerToggle state={{ ...state, season }} />
              </div>
            }
          />
          <p className="mb-8 max-w-3xl text-sm leading-relaxed text-muted-foreground">
            The small number and the bar are each player&apos;s percentile among {peerDescription(comparison)} in{" "}
            {season}
            {season === meta.current_season
              ? " so far"
              : " with at least 20 games"}
            , with turnovers and defensive rating flipped so a longer bar is always better. The best value in each row is
            in bold.
            {season === meta.current_season && (
              <span className="mt-2 block border-l-2 border-brand pl-3">
                {season} is under way: these numbers are as of{" "}
                {meta.current_season_as_of ? shortDate(meta.current_season_as_of) : "the last update"}, and the
                percentiles count everyone who has played so far, so expect them to move. Pick an earlier season for
                settled numbers.
              </span>
            )}
          </p>
          <ComparisonTable comparison={comparison} colors={PLAYER_COLORS} leaders={leaders!} />
        </Section>
      )}
    </>
  );
}

/** The franchise's colours with the abbreviation the team used that season (e.g. "NJN" for the Nets). */
function teamThen(teams: Map<string, TeamSummary>, franchise: string, abbrThen: string) {
  const team = teams.get(franchise);
  return team ? { ...team, abbr: abbrThen } : undefined;
}

/** The empty page: how to start, and a ready-made matchup from the latest MVP race. */
async function Start({ meta, state }: { meta: Meta; state: CompareState }) {
  const race = await getMvpRace(meta.last_season);
  const top = race?.candidates.slice(0, 3) ?? [];
  return (
    <>
      Pick an open slot to add the first player
      {top.length === 3 ? (
        <>
          , or start with the top three of the {race!.season} MVP race:{" "}
          <Link
            href={`${compareHref({ ids: top.map((c) => c.player.id), peers: state.peers, show: true })}#head-to-head`}
            className="font-medium text-foreground underline decoration-brand underline-offset-4 hover:text-brand"
          >
            {top.map((c) => c.player.name).join(", ")}
          </Link>
          .
        </>
      ) : (
        "."
      )}
    </>
  );
}

/** What can be added: search matches, or suggestions when nothing has been typed. */
async function Candidates({ state, profiles, meta }: { state: CompareState; profiles: PlayerProfile[]; meta: Meta }) {
  const add = (id: number) => compareHref(withPlayer(state, id));
  const chosen = new Set(state.ids);

  if (state.q) {
    const page = await searchPlayers({ q: state.q, limit: 8, offset: 0 });
    const matches: Candidate[] = page.items
      .filter((p) => !chosen.has(p.id))
      .map((p) => ({
        player: p,
        detail: `${p.position ?? p.position_group} · ${seasonSpan(p.first_season, p.last_season)}`,
        href: add(p.id),
      }));
    if (matches.length === 0) {
      return <p className="mt-3 text-sm text-muted-foreground">No other players match &ldquo;{state.q}&rdquo;.</p>;
    }
    return <CandidateList candidates={matches} />;
  }

  if (profiles.length === 1) {
    const [only] = profiles;
    const similar = await getSimilarPlayers(only.id);
    if (!similar) return null;
    return (
      <CandidateList
        title={`Closest in style to ${only.name}, ${similar.season}`}
        candidates={similar.similar.map((s) => ({
          player: s.player,
          detail: `${s.team_abbr} · ${s.archetype ?? "No role"}`,
          href: add(s.player.id),
        }))}
      />
    );
  }

  if (profiles.length === 0) {
    const race = await getMvpRace(meta.last_season);
    if (!race) return null;
    const top = race.candidates.slice(0, 4);
    return (
      <>
        <CandidateList
          title={`Top of the ${race.season} MVP race`}
          candidates={top.map((c) => ({
            player: c.player,
            detail: `${c.team.abbr} · ${c.is_mvp ? "MVP" : `${c.rank} in the model's ranking`}`,
            href: add(c.player.id),
          }))}
        />
        <Link
          href={`${compareHref({ ids: top.slice(0, 3).map((c) => c.player.id), peers: state.peers, show: true })}#head-to-head`}
          className="eyebrow mt-4 inline-flex h-9 items-center bg-foreground px-4 text-background hover:bg-brand hover:text-brand-foreground"
        >
          Compare the top three →
        </Link>
      </>
    );
  }

  return null;
}

function NoSharedSeason({ profiles, state }: { profiles: PlayerProfile[]; state: CompareState }) {
  return (
    <div className="mt-10 border-y py-6">
      <p className="font-display text-2xl font-bold tracking-tight uppercase">No season in common</p>
      <p className="mt-2 text-muted-foreground">
        These players were never in the league in the same season, so there is nothing to line up. Remove one:
      </p>
      <ul className="mt-3 flex flex-col gap-1 text-sm">
        {profiles.map((p) => (
          <li key={p.id}>
            <Link
              href={compareHref({ ...withoutPlayer(state, p.id), q: undefined })}
              scroll={false}
              className="text-brand underline-offset-4 hover:underline"
            >
              Remove {p.name}
            </Link>{" "}
            <span className="tabular text-muted-foreground">({seasonSpan(p.first_season, p.last_season)})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CompareSkeleton() {
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-44 w-full" />
        ))}
      </div>
      <Skeleton className="mt-6 h-12 w-full max-w-3xl" />
      <Skeleton className="mt-14 h-96 w-full" />
    </>
  );
}
