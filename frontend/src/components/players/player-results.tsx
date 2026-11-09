import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { TeamBadge } from "@/components/team-badge";
import type { PlayerPage, PlayerSummary } from "@/lib/api/client";
import { seasonSpan } from "@/lib/format";
import { PAGE_SIZE, type PlayerFilters, playersHref } from "@/lib/player-search";
import { cn } from "@/lib/utils";

const NUMBER = new Intl.NumberFormat("en-US");

function summary(total: number, filters: PlayerFilters): string {
  const players = `${NUMBER.format(total)} ${total === 1 ? "player" : "players"}`;
  return filters.q ? `${players} matching “${filters.q}”` : players;
}

/** One page of search results: a row per player linking to their profile, then page links. */
export function PlayerResults({ page, filters }: { page: PlayerPage; filters: PlayerFilters }) {
  const pages = Math.max(1, Math.ceil(page.total / PAGE_SIZE));

  if (page.total === 0) {
    return (
      <div className="border-y-2 border-foreground py-12 text-center">
        <p className="font-display text-3xl font-bold uppercase">No players found</p>
        <p className="mt-2 text-muted-foreground">
          Check the spelling, or{" "}
          <Link href="/players" className="text-brand underline-offset-4 hover:underline">
            clear the filters
          </Link>
          .
        </p>
      </div>
    );
  }

  if (page.items.length === 0) {
    return (
      <p className="border-y py-8 text-muted-foreground">
        There is no page {filters.page}.{" "}
        <Link href={playersHref({ ...filters, page: 1 })} className="text-brand hover:underline">
          Back to the first page
        </Link>
      </p>
    );
  }

  const from = page.offset + 1;
  const to = page.offset + page.items.length;

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b-2 border-foreground pb-2">
        <p className="font-display text-xl font-bold tracking-tight uppercase" aria-live="polite">
          {summary(page.total, filters)}
        </p>
        <p className="tabular text-sm text-muted-foreground">
          {from}–{to} of {NUMBER.format(page.total)}
        </p>
      </div>

      <div className="eyebrow hidden grid-cols-[minmax(0,1fr)_5rem_11rem_12rem] gap-4 border-b py-2 text-muted-foreground md:grid" aria-hidden="true">
        <span>Player</span>
        <span>Position</span>
        <span>Seasons</span>
        <span>Team</span>
      </div>
      <ol>
        {page.items.map((player) => (
          <li
            key={player.id}
            className="group relative grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b py-2.5 transition-colors hover:bg-muted/40 md:grid-cols-[minmax(0,1fr)_5rem_11rem_12rem]"
          >
            <span className="flex min-w-0 items-center gap-3">
              <PlayerAvatar player={player} />
              <span className="min-w-0">
                {/* The link covers the whole row; the other cells stay plain text for screen readers. */}
                <Link
                  href={`/players/${player.id}`}
                  className="block truncate font-medium after:absolute after:inset-0 group-hover:text-brand focus-visible:outline-none after:focus-visible:outline-2 after:focus-visible:outline-ring"
                >
                  {player.name}
                </Link>
                <span className="tabular block text-xs text-muted-foreground md:hidden">
                  {player.position ?? player.position_group} · {seasonSpan(player.first_season, player.last_season)}
                </span>
              </span>
            </span>
            <span className="hidden text-sm text-muted-foreground md:block">{player.position ?? player.position_group}</span>
            <span className="tabular hidden text-sm text-muted-foreground md:block">
              {seasonSpan(player.first_season, player.last_season)}
            </span>
            <TeamCell player={player} />
          </li>
        ))}
      </ol>

      {pages > 1 && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4">
          <PageLink filters={filters} page={filters.page - 1} disabled={filters.page <= 1}>
            ← Previous
          </PageLink>
          <span className="tabular text-sm text-muted-foreground">
            Page {filters.page} of {pages}
          </span>
          <PageLink filters={filters} page={filters.page + 1} disabled={filters.page >= pages}>
            Next →
          </PageLink>
        </nav>
      )}
    </div>
  );
}

/** The player's team today; for players not on a roster, their last team, faded and labelled as such. */
function TeamCell({ player }: { player: PlayerSummary }) {
  const team = player.current_team ?? player.latest_team;
  const label = player.current_team ? team.name : `Last: ${team.name}, ${player.last_season}`;
  return (
    <span className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground" title={label}>
      <TeamBadge team={team} className={player.current_team ? undefined : "opacity-50"} />
      <span className={cn("truncate", player.current_team ? "hidden lg:inline" : "sr-only lg:not-sr-only lg:inline")}>
        {player.current_team ? team.name : `Last: ${team.name}`}
      </span>
    </span>
  );
}

function PageLink({
  filters,
  page,
  disabled,
  children,
}: {
  filters: PlayerFilters;
  page: number;
  disabled: boolean;
  children: React.ReactNode;
}) {
  const className = "eyebrow inline-flex h-9 items-center border px-4";
  if (disabled) {
    return (
      <span className={cn(className, "text-muted-foreground/50")} aria-hidden="true">
        {children}
      </span>
    );
  }
  return (
    <Link href={playersHref({ ...filters, page })} className={cn(className, "hover:border-foreground hover:text-brand")}>
      {children}
    </Link>
  );
}
