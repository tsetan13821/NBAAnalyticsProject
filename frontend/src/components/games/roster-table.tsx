import { CircleAlertIcon, CircleCheckIcon, CircleHelpIcon, CircleXIcon } from "lucide-react";
import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { TeamBadge } from "@/components/team-badge";
import type { GamePlayer, TeamRef } from "@/lib/api/client";
import { choiceOf, gameHref, type WhatIfChoice, type WhatIfState, withChoice } from "@/lib/games";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<NonNullable<GamePlayer["status"]>, { icon: typeof CircleXIcon; className: string }> = {
  Out: { icon: CircleXIcon, className: "text-miss" },
  Doubtful: { icon: CircleXIcon, className: "text-miss" },
  Questionable: { icon: CircleHelpIcon, className: "text-chart-4" },
  Probable: { icon: CircleCheckIcon, className: "text-muted-foreground" },
  Available: { icon: CircleCheckIcon, className: "text-muted-foreground" },
};

/** Players who barely matter to the prediction are folded away (still shown if listed or changed). */
const MINOR_VALUE = 0.5;

export function StatusLabel({ player }: { player: GamePlayer }) {
  if (!player.status) {
    if (player.chance < 0.9) {
      return (
        <span className="inline-flex items-center gap-1 text-muted-foreground" title="Not on the injury report, but sat out some recent games">
          <CircleAlertIcon className="size-3.5" aria-hidden="true" />
          Out of the rotation lately
        </span>
      );
    }
    return <span className="text-muted-foreground">Not listed</span>;
  }
  const { icon: Icon, className } = STATUS_STYLE[player.status];
  return (
    <span className={cn("inline-flex items-center gap-1 font-medium", className)}>
      <Icon className="size-3.5" aria-hidden="true" />
      {player.status}
      {player.status_source === "carried" && <span className="font-normal text-muted-foreground">(latest)</span>}
    </span>
  );
}

const CHOICES: { choice: WhatIfChoice; label: string }[] = [
  { choice: null, label: "Report" },
  { choice: "out", label: "Sits" },
  { choice: "in", label: "Plays" },
];

function WhatIfControl({
  gameId,
  state,
  player,
}: {
  gameId: string;
  state: WhatIfState;
  player: GamePlayer;
}) {
  const current = choiceOf(state, player.id);
  return (
    <div role="group" aria-label={`What if for ${player.name}`} className="inline-flex rounded border text-xs">
      {CHOICES.map(({ choice, label }) => {
        const active = current === choice;
        return (
          <Link
            key={label}
            href={gameHref(gameId, withChoice(state, player.id, choice))}
            scroll={false}
            replace
            aria-current={active ? "true" : undefined}
            aria-label={`${player.name}: ${choice === null ? "as on the injury report" : label.toLowerCase()}`}
            className={cn(
              "px-2 py-1 transition-colors first:rounded-l last:rounded-r",
              active ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}

function PlayerRow({ player, gameId, state, editable }: { player: GamePlayer; gameId: string; state: WhatIfState; editable: boolean }) {
  return (
    <tr className={cn("border-b align-middle", player.what_if && "bg-muted/50")}>
      <td className="py-2 pr-3">
        <span className="flex min-w-0 items-center gap-2.5">
          <PlayerAvatar player={player} size="sm" />
          <span className="min-w-0">
            <span className="block truncate font-medium">{player.name}</span>
            <span className="block truncate text-xs">
              <StatusLabel player={player} />
              {player.reason && player.reason !== "-" && (
                <span className="text-muted-foreground"> · {player.reason.replace(/^Injury\/Illness - /, "")}</span>
              )}
            </span>
          </span>
        </span>
      </td>
      <td className="tabular py-2 pr-3 text-right">{player.value.toFixed(1)}</td>
      <td className="tabular py-2 pr-3 text-right text-muted-foreground">{Math.round(player.expected_minutes)}</td>
      <td className="tabular py-2 pr-3 text-right font-semibold">
        {player.played === null ? `${Math.round(player.chance * 100)}%` : player.played ? "Played" : "Sat"}
      </td>
      {editable && (
        <td className="py-2 text-right">
          <WhatIfControl gameId={gameId} state={state} player={player} />
        </td>
      )}
    </tr>
  );
}

/**
 * A team's players, most valuable first: value, usual minutes, injury status and chance of playing,
 * with controls to sit or play anyone (`editable`, for games not yet played).
 */
export function RosterTable({
  team,
  players,
  gameId,
  state,
  editable,
}: {
  team: TeamRef;
  players: GamePlayer[];
  gameId: string;
  state: WhatIfState;
  editable: boolean;
}) {
  const main = players.filter((p) => p.value >= MINOR_VALUE || p.status || p.what_if);
  const minor = players.filter((p) => !main.includes(p));
  const head = (
    <thead>
      <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
        <th scope="col" className="py-2 pr-3 font-semibold">Player</th>
        <th scope="col" className="py-2 pr-3 text-right font-semibold" title="Game Score above a replacement player, at his usual minutes">
          Value
        </th>
        <th scope="col" className="py-2 pr-3 text-right font-semibold">Min</th>
        <th scope="col" className="py-2 pr-3 text-right font-semibold">{editable ? "Plays" : "Result"}</th>
        {editable && (
          <th scope="col" className="py-2 text-right font-semibold">
            What if
          </th>
        )}
      </tr>
    </thead>
  );
  return (
    <div className="min-w-0">
      <h3 className="mb-2 flex items-center gap-2 font-display text-xl font-bold uppercase">
        <TeamBadge team={team} />
        {team.name}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[30rem] text-sm">
          {head}
          <tbody>
            {main.map((p) => (
              <PlayerRow key={p.id} player={p} gameId={gameId} state={state} editable={editable} />
            ))}
          </tbody>
        </table>
      </div>
      {minor.length > 0 && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            {minor.length} more {minor.length === 1 ? "player" : "players"} who barely move the prediction
          </summary>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[30rem] text-sm">
              <tbody>
                {minor.map((p) => (
                  <PlayerRow key={p.id} player={p} gameId={gameId} state={state} editable={editable} />
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
