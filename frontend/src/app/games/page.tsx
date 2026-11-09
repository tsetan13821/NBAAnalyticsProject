import { ArrowRightIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { ConfidenceTable, GameCard } from "@/components/games/game-parts";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { getGameResults, getUpcomingGames } from "@/lib/api/client";
import { percent, ratio } from "@/lib/format";
import { byDate, easternStamp, longDate } from "@/lib/games";

export const metadata: Metadata = {
  title: "Game predictor",
  description:
    "Win probability and predicted margin for every NBA game in the coming week, from team strength, form, rest and travel, and the official injury report.",
};

const RECENT_RESULTS = 6;

export default function GamesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Game predictor"
        title="Who wins this week"
        lede="Every game in the next seven days: each team's chance, the predicted margin, and the players the injury report says may miss it. Open a game to see why, and to change who plays."
        actions={
          <Link href="/games/method" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
            How it works <ArrowRightIcon className="size-3.5" />
          </Link>
        }
      />
      <Suspense fallback={<GamesSkeleton />}>
        <Upcoming />
      </Suspense>
      <Suspense fallback={<Skeleton className="mt-16 h-64 w-full" />}>
        <SeasonSoFar />
      </Suspense>
    </>
  );
}

async function Upcoming() {
  const upcoming = await getUpcomingGames();
  const report = easternStamp(upcoming.injury_report);
  return (
    <Section>
      <SectionHeading
        number="01"
        title="Coming up"
        aside={report ? `Injury report of ${report}` : "No injury report yet"}
      />
      {upcoming.games.length === 0 ? (
        <p className="text-muted-foreground">No games in the next seven days.</p>
      ) : (
        <div className="space-y-10">
          {byDate(upcoming.games).map(([day, games]) => (
            <div key={day}>
              <h3 className="mb-3 font-display text-xl font-bold uppercase">
                {longDate(day)}
                <span className="ml-3 text-sm font-normal text-muted-foreground normal-case">
                  {games.length} {games.length === 1 ? "game" : "games"}
                </span>
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {games.map((game) => (
                  <GameCard key={game.game_id} game={game} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="mt-6 max-w-2xl text-sm text-muted-foreground">
        Games beyond the latest report carry each player&apos;s latest Out or Doubtful status forward, so they firm up
        closer to tip-off. Predictions as of {easternStamp(upcoming.as_of) ?? "the last data refresh"}.
      </p>
    </Section>
  );
}

async function SeasonSoFar() {
  const results = await getGameResults(RECENT_RESULTS);
  const { record } = results;
  if (record.games === 0) return null;
  return (
    <Section>
      <SectionHeading
        number="02"
        title={`${record.season} so far`}
        aside={
          <Link href="/games/results" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
            Every result <ArrowRightIcon className="size-3.5" />
          </Link>
        }
      />
      <FigureRow>
        <Figure
          label="Winners called"
          value={ratio(record.correct, record.games)}
          detail={`${percent(record.accuracy ?? 0)}, each predicted before tip-off`}
          tone="brand"
        />
        <Figure label="Home team won" value={percent(record.home_team_won ?? 0)} detail="Always picking them" />
      </FigureRow>
      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
        <div>
          <h3 className="mb-3 font-display text-xl font-bold uppercase">Latest results</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            {results.items.map((game) => (
              <GameCard key={game.game_id} game={game} />
            ))}
          </div>
        </div>
        <div>
          <h3 className="mb-3 font-display text-xl font-bold uppercase">Is it honest?</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            When the model gives a team 70%, that team should win about 7 times in 10. Early-season numbers are
            noisy: each row needs a few hundred games to settle.
          </p>
          <ConfidenceTable record={record} />
        </div>
      </div>
    </Section>
  );
}

function GamesSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-44 w-full" />
      ))}
    </div>
  );
}
