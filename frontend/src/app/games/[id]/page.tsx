import { ArrowLeftIcon, RotateCcwIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { BreakdownChart, ChanceBar, KeyAbsences, Verdict } from "@/components/games/game-parts";
import { RosterTable } from "@/components/games/roster-table";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { type GameDetail, getGame } from "@/lib/api/client";
import { chances, gameHref, hasWhatIf, longDate, marginText, parseWhatIf, tipTime, type WhatIfState } from "@/lib/games";

const GAME_ID = /^\d{10}$/;

export async function generateMetadata({ params }: PageProps<"/games/[id]">): Promise<Metadata> {
  const { id } = await params;
  const game = GAME_ID.test(id) ? await getGame(id) : null;
  if (!game) return { title: "Game not found" };
  return {
    title: `${game.away.team.name} at ${game.home.team.name}`,
    description: `${marginText(game.predicted_margin, game.home.team.abbr, game.away.team.abbr)}: the prediction, why, and who is available.`,
  };
}

export default function GamePage({ params, searchParams }: PageProps<"/games/[id]">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <Game params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function Game({ params, searchParams }: PageProps<"/games/[id]">) {
  const { id } = await params;
  if (!GAME_ID.test(id)) notFound();
  const base = await getGame(id);
  if (!base) notFound();

  // What-ifs apply to games not yet played, and only to players in this game (a stale link keeps the rest).
  const editable = base.result === null;
  const roster = new Set([...base.home_players, ...base.away_players].map((p) => p.id));
  const requested = parseWhatIf(await searchParams);
  const state: WhatIfState = editable
    ? { out: requested.out.filter((p) => roster.has(p)), in: requested.in.filter((p) => roster.has(p)) }
    : { out: [], in: [] };
  const game = hasWhatIf(state) ? ((await getGame(id, state.out, state.in)) ?? base) : base;

  const { home, away } = game;
  const odds = chances(game.home_win_probability);
  const favourite = odds.home >= odds.away ? home : away;
  const when = game.result ? `Final · ${longDate(game.date)}` : `${longDate(game.date)} · ${tipTime(game.tip_et) ?? "time to be set"}`;

  return (
    <>
      <Link href="/games" className="eyebrow mb-6 inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" /> All games
      </Link>
      <PageHeader
        eyebrow={when}
        title={
          <>
            {away.team.name}
            <span className="block text-muted-foreground">at {home.team.name}</span>
          </>
        }
        lede={`${away.team.name} ${away.wins}-${away.losses}, ${home.team.name} ${home.wins}-${home.losses} before the game.`}
      />

      {game.what_if && <WhatIfBanner game={game} />}

      <FigureRow>
        <Figure
          label={`${favourite.team.abbr} win chance`}
          value={`${Math.max(odds.home, odds.away)}%`}
          detail={game.result ? "Before tip-off" : undefined}
          tone="brand"
        />
        <Figure
          label={Math.abs(game.predicted_margin) < 0.5 ? "Predicted margin" : `${favourite.team.abbr} predicted margin`}
          value={`+${Math.abs(game.predicted_margin).toFixed(1)}`}
          detail="Points"
        />
        {game.result && (
          <Figure
            label={`Final, ${away.team.abbr}–${home.team.abbr}`}
            value={`${game.result.away_pts}–${game.result.home_pts}`}
            detail={<Verdict game={game} />}
          />
        )}
      </FigureRow>
      <div className="mt-6 max-w-2xl">
        <ChanceBar game={game} size="lg" />
        <div className="mt-3">
          <KeyAbsences game={base} />
        </div>
      </div>

      <Section>
        <SectionHeading number="01" title="Why" />
        <div className="max-w-3xl">
          <BreakdownChart items={game.breakdown} margin={game.predicted_margin} home={home.team.abbr} away={away.team.abbr} />
          <p className="mt-6 font-serif text-[1.0625rem] leading-relaxed text-muted-foreground">
            Each line is the points it adds to the home team&apos;s predicted margin. The real margin lands within about{" "}
            {Math.round(game.spread)} points of the prediction two times in three, which is where the win chance comes
            from. <Link href="/games/method" className="text-brand hover:underline">How the model works</Link>.
          </p>
        </div>
      </Section>

      <Section>
        <SectionHeading
          number="02"
          title={editable ? "Who plays" : "Who played"}
          aside={
            hasWhatIf(state) && (
              <Link href={gameHref(id)} scroll={false} replace className="inline-flex items-center gap-1.5 text-brand hover:underline">
                <RotateCcwIcon className="size-3.5" /> Back to the injury report
              </Link>
            )
          }
        />
        <p className="mb-6 max-w-3xl text-sm text-muted-foreground">
          <strong className="font-medium text-foreground">Value</strong> is how much a player adds over a replacement
          at his usual minutes, in points of Game Score. A star is worth 10 to 20; a deep reserve, nothing. Minutes go
          to the best players first, so losing a starter costs less than his full value when a good backup steps in.
          {editable && " Sit or play anyone to see how the prediction moves."}
        </p>
        <div className="grid max-w-4xl gap-12">
          <RosterTable team={away.team} players={game.away_players} gameId={id} state={state} editable={editable} />
          <RosterTable team={home.team} players={game.home_players} gameId={id} state={state} editable={editable} />
        </div>
      </Section>
    </>
  );
}

function WhatIfBanner({ game }: { game: GameDetail }) {
  const whatIf = game.what_if!;
  const before = chances(whatIf.base_home_win_probability);
  const after = chances(game.home_win_probability);
  const names = new Map([...game.home_players, ...game.away_players].map((p) => [p.id, p.name]));
  const list = (ids: number[]) => ids.map((pid) => names.get(pid)).join(", ");
  return (
    <aside className="mb-8 border-l-[3px] border-brand bg-paper py-3 pr-5 pl-5 text-sm" aria-live="polite">
      <p className="eyebrow text-brand">What if</p>
      <p className="mt-1">
        {whatIf.out.length > 0 && <>Without {list(whatIf.out)}. </>}
        {whatIf.in.length > 0 && <>With {list(whatIf.in)} playing. </>}
        <span className="tabular font-semibold">
          {game.home.team.abbr} {before.home}% → {after.home}%
        </span>
        <span className="text-muted-foreground">
          {" "}
          (was {marginText(whatIf.base_predicted_margin, game.home.team.abbr, game.away.team.abbr)})
        </span>
      </p>
    </aside>
  );
}
