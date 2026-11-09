/** The pieces of a game prediction: the chance bar, the card, the "why" breakdown, the track record. */
import { CheckIcon, XIcon } from "lucide-react";
import Link from "next/link";

import { TeamBadge } from "@/components/team-badge";
import type { BreakdownItem, GameSummary, TrackRecord } from "@/lib/api/client";
import { chances, gameHref, marginText, signedPoints, tipTime } from "@/lib/games";
import { cn } from "@/lib/utils";

/**
 * The home team's chance as one whole split in two: away on the left in the away colour, home on the
 * right in the home colour, each labelled with its team and percentage (so colour is never the only cue).
 */
export function ChanceBar({
  game,
  size = "sm",
}: {
  game: Pick<GameSummary, "home" | "away" | "home_win_probability">;
  size?: "sm" | "lg";
}) {
  const { home, away } = chances(game.home_win_probability);
  const label = (abbr: string, pct: number, favourite: boolean) => (
    <span className={cn("tabular whitespace-nowrap", favourite ? "font-bold text-foreground" : "text-muted-foreground")}>
      {abbr} {pct}%
    </span>
  );
  return (
    <div
      className={cn("flex items-center gap-2", size === "lg" ? "text-lg" : "text-sm")}
      role="img"
      aria-label={`${game.away.team.name} ${away}%, ${game.home.team.name} ${home}%`}
    >
      {label(game.away.team.abbr, away, away > home)}
      <div className={cn("flex min-w-0 flex-1 gap-0.5", size === "lg" ? "h-4" : "h-2.5")} aria-hidden="true">
        <div className="rounded-l-[4px] bg-away" style={{ width: `${away}%` }} title={`${game.away.team.abbr} ${away}%`} />
        <div className="rounded-r-[4px] bg-home" style={{ width: `${home}%` }} title={`${game.home.team.abbr} ${home}%`} />
      </div>
      {label(game.home.team.abbr, home, home >= away)}
    </div>
  );
}

function Side({ side, where }: { side: GameSummary["home"]; where: string }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <TeamBadge team={side.team} />
      <span className="truncate font-medium">{side.team.name}</span>
      <span className="tabular shrink-0 text-xs text-muted-foreground">
        {side.wins}-{side.losses}
        <span className="sr-only"> {where}</span>
      </span>
    </span>
  );
}

/** Result of a played game against the prediction. */
export function Verdict({ game }: { game: GameSummary }) {
  if (!game.result) return null;
  const { correct } = game.result;
  const Icon = correct ? CheckIcon : XIcon;
  return (
    <span className={cn("eyebrow inline-flex items-center gap-1", correct ? "text-hit" : "text-miss")}>
      <Icon className="size-3.5" aria-hidden="true" />
      {correct ? "Called it" : "Missed"}
    </span>
  );
}

/** One game in a list: teams, chance, margin, and who is missing. Links to the game page. */
export function GameCard({ game }: { game: GameSummary }) {
  const { home, away, result } = game;
  return (
    <Link
      href={gameHref(game.game_id)}
      className="group flex flex-col gap-3 border-t-2 border-foreground bg-paper p-4 transition-colors hover:bg-muted/40"
    >
      <span className="eyebrow flex justify-between text-muted-foreground">
        <span>{result ? "Final" : (tipTime(game.tip_et) ?? "Time to be set")}</span>
        {result ? <Verdict game={game} /> : <span className="text-brand">{marginText(game.predicted_margin, home.team.abbr, away.team.abbr)}</span>}
      </span>
      <span className="grid gap-1.5 text-sm">
        <span className="flex items-center justify-between gap-2">
          <Side side={away} where="away" />
          {result && <span className="tabular font-display text-xl font-bold">{result.away_pts}</span>}
        </span>
        <span className="flex items-center justify-between gap-2">
          <Side side={home} where="at home" />
          {result && <span className="tabular font-display text-xl font-bold">{result.home_pts}</span>}
        </span>
      </span>
      <ChanceBar game={game} />
      <KeyAbsences game={game} />
    </Link>
  );
}

export function KeyAbsences({ game }: { game: GameSummary }) {
  const shown = game.key_absences.filter((a) => !a.already_missing);
  const longTerm = game.key_absences.length - shown.length;
  if (game.key_absences.length === 0) {
    return <p className="text-xs text-muted-foreground">No key players listed on the injury report.</p>;
  }
  return (
    <p className="text-xs leading-relaxed text-muted-foreground">
      {shown.map((a, i) => (
        <span key={a.player_id}>
          {i > 0 && ", "}
          <span className="font-medium text-foreground">{a.name}</span> ({a.team_abbr}, {a.status.toLowerCase()})
        </span>
      ))}
      {longTerm > 0 && (
        <span>
          {shown.length > 0 && "; "}
          {longTerm} long-term {longTerm === 1 ? "absence" : "absences"} already priced in
        </span>
      )}
    </p>
  );
}

/**
 * Where the predicted margin comes from: one diverging bar per group of inputs, toward the away team
 * (left, away colour) or the home team (right, home colour), each labelled with its points.
 */
export function BreakdownChart({
  items,
  margin,
  home,
  away,
}: {
  items: BreakdownItem[];
  margin: number;
  home: string;
  away: string;
}) {
  const scale = Math.max(3, ...items.map((i) => Math.abs(i.points)));
  const width = (points: number) => `${(Math.abs(points) / scale) * 100}%`;
  return (
    <figure>
      <div className="eyebrow grid grid-cols-[6.5rem_1fr_1fr] sm:grid-cols-[11rem_1fr_1fr] gap-x-3 pb-2 text-muted-foreground">
        <span />
        <span className="flex items-center justify-end gap-1.5 whitespace-nowrap">
          <span aria-hidden="true" className="max-sm:hidden">←</span> {away}
          <span className="size-2.5 rounded-sm bg-away" aria-hidden="true" />
        </span>
        <span className="flex items-center gap-1.5 whitespace-nowrap">
          <span className="size-2.5 rounded-sm bg-home" aria-hidden="true" />
          {home} <span aria-hidden="true" className="max-sm:hidden">→</span>
        </span>
      </div>
      <dl className="border-t">
        {items.map((item) => (
          <div
            key={item.key}
            className="grid grid-cols-[6.5rem_1fr_1fr] sm:grid-cols-[11rem_1fr_1fr] items-center gap-x-3 border-b py-2 text-sm"
            title={`${item.label}: ${signedPoints(item.points)} points toward ${item.points >= 0 ? home : away}`}
          >
            <dt className="text-xs leading-tight sm:truncate sm:text-sm">{item.label}</dt>
            <dd className="flex items-center justify-end gap-2 border-r border-foreground/40 pr-0 [grid-column:2]">
              {item.points < 0 && (
                <>
                  <span className="tabular text-xs text-muted-foreground">{signedPoints(item.points)}</span>
                  <span className="h-3 rounded-l-[4px] bg-away" style={{ width: width(item.points) }} />
                </>
              )}
            </dd>
            <dd className="flex items-center gap-2 [grid-column:3]">
              {item.points > 0 && (
                <>
                  <span className="h-3 rounded-r-[4px] bg-home" style={{ width: width(item.points) }} />
                  <span className="tabular text-xs text-muted-foreground">{signedPoints(item.points)}</span>
                </>
              )}
            </dd>
          </div>
        ))}
      </dl>
      <figcaption className="mt-3 flex justify-between gap-4 text-sm">
        <span className="text-muted-foreground">Points toward each side; they add up to the prediction</span>
        <span className="tabular font-semibold">
          {signedPoints(margin)} · {marginText(margin, home, away)}
        </span>
      </figcaption>
    </figure>
  );
}

/** How often the favourite won at each level of confidence, against how sure the model was. */
export function ConfidenceTable({ record }: { record: TrackRecord }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[20rem] text-sm">
        <caption className="sr-only">How often the model&apos;s favourite won, by how confident it was</caption>
        <thead>
          <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-semibold">Favourite&apos;s chance</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Games</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Predicted</th>
            <th scope="col" className="py-2 text-right font-semibold">Favourite won</th>
          </tr>
        </thead>
        <tbody>
          {record.by_confidence.map((bin) => (
            <tr key={bin.low} className="border-b">
              <td className="tabular py-2 pr-4">
                {Math.round(bin.low * 100)}–{Math.round(bin.high * 100)}%
              </td>
              <td className="tabular py-2 pr-4 text-right">{bin.games}</td>
              <td className="tabular py-2 pr-4 text-right text-muted-foreground">{Math.round(bin.predicted * 100)}%</td>
              <td className="tabular py-2 text-right font-semibold">
                {Math.round((bin.favorite_won / bin.games) * 100)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
