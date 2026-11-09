import { TrophyIcon } from "lucide-react";
import Link from "next/link";

import { PlayerPhoto } from "@/components/players/player-photo";
import { TeamBadge } from "@/components/team-badge";
import type { PlayerProfile } from "@/lib/api/client";
import { height, ordinal, seasonSpan, shortDate } from "@/lib/format";

const POSITION_NAMES: Record<string, string> = { G: "Guard", F: "Forward", C: "Center" };

/** "G-F" -> "Guard-Forward" */
export function positionName(position: string | null, group: string): string {
  return (position ?? group)
    .split("-")
    .map((p) => POSITION_NAMES[p] ?? p)
    .join("-");
}

/** "2014 · Round 2, 41st pick", or "Undrafted" */
export function draftText(profile: Pick<PlayerProfile, "draft_year" | "draft_round" | "draft_number">): string {
  const { draft_year: year, draft_round: round, draft_number: pick } = profile;
  if (!year) return "Undrafted";
  const details = [round && `round ${round}`, pick && `${ordinal(pick)} pick`].filter(Boolean).join(", ");
  return details ? `${year}, ${details}` : String(year);
}

/**
 * Name, team, bio facts and MVP awards, beside a large headshot on a band of the team's colour.
 *
 * The team shown is the player's team today (from NBA.com rosters on `rostersAsOf`), which can differ
 * from the team in the last season of stats; retired players and free agents show their last team.
 */
export function PlayerHero({ profile, rostersAsOf }: { profile: PlayerProfile; rostersAsOf: string }) {
  const { current_team: current, latest_team: latest } = profile;
  const moved = current !== null && current.abbr !== latest.abbr;
  const facts = [
    { label: "Position", value: positionName(profile.position, profile.position_group) },
    profile.height_in && {
      label: "Size",
      value: `${height(profile.height_in)}${profile.weight_lb ? `, ${profile.weight_lb} lb` : ""}`,
    },
    profile.country && { label: "From", value: profile.country },
    profile.college && { label: "Before the NBA", value: profile.college },
    { label: "Draft", value: draftText(profile) },
    {
      label: "In this data",
      value: `${seasonSpan(profile.first_season, profile.last_season)} · ${profile.seasons_played} ${profile.seasons_played === 1 ? "season" : "seasons"}`,
    },
  ].filter((fact): fact is { label: string; value: string } => Boolean(fact));

  return (
    <header className="mb-12 grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:items-end">
      <div className="order-2 md:order-1">
        <p className="eyebrow mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
          <TeamBadge team={current ?? latest} className={current ? undefined : "opacity-60"} />
          {current ? (
            <>
              <span className="text-brand">{current.name}</span>
              <span className="text-muted-foreground">· Roster as of {shortDate(rostersAsOf)}</span>
            </>
          ) : (
            <span className="text-muted-foreground">
              Last played for the {latest.name}, {profile.last_season}
            </span>
          )}
        </p>
        <h1 className="font-display text-5xl leading-[0.92] font-bold tracking-tight uppercase sm:text-7xl">
          {profile.name}
        </h1>
        {profile.mvp_seasons.length > 0 && (
          <p className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="eyebrow inline-flex items-center gap-1.5 text-brand">
              <TrophyIcon className="size-3.5" aria-hidden="true" />
              {profile.mvp_seasons.length > 1 ? `${profile.mvp_seasons.length}× MVP` : "MVP"}
            </span>
            {profile.mvp_seasons.map((season) => (
              <Link
                key={season}
                href={`/mvp/${season}`}
                className="tabular text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                {season}
              </Link>
            ))}
          </p>
        )}
        {moved && (
          <p className="mt-4 max-w-xl border-l-2 border-brand pl-3 text-sm text-muted-foreground">
            Now with the {current.name}. The numbers on this page run to {profile.last_season}, when the player was
            with the {latest.name}.
          </p>
        )}
        <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 border-t pt-4 sm:grid-cols-3">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dt className="eyebrow text-muted-foreground">{fact.label}</dt>
              <dd className="mt-0.5 text-sm font-medium">{fact.value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <PlayerPhoto
        player={profile}
        color={(current ?? latest).primary_color}
        className="order-1 md:order-2"
      />
    </header>
  );
}
