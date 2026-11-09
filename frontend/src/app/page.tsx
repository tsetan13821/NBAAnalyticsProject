import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { SeasonStrip } from "@/components/mvp/season-strip";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { getMeta, getMvpOverview } from "@/lib/api/client";
import { percent, ratio } from "@/lib/format";
import { cn } from "@/lib/utils";

const CONTENTS: { title: string; description: string; href?: string }[] = [
  {
    title: "MVP Race",
    description: "The model's pick against the real winner for every season, and the full field of contenders.",
    href: "/mvp",
  },
  {
    title: "How the MVP model works",
    description: "The rules, features, settings and validation, with every design decision and its trade-off.",
    href: "/mvp/method",
  },
  {
    title: "Players",
    description: "Every player since 2000: season-by-season numbers, career arc and the most similar players.",
    href: "/players",
  },
  {
    title: "Game predictor",
    description: "Every game this week: each team's chance, the predicted margin, and who the injury report says may miss it.",
    href: "/games",
  },
  {
    title: "How the game predictor works",
    description: "Team strength, player value, the injury report, and how the model was tested on unseen seasons.",
    href: "/games/method",
  },
  { title: "Franchises", description: "Records, rosters and championships for all 30 teams." },
];

export default function HomePage() {
  return (
    <>
      <PageHeader
        eyebrow="NBA.com data · 2000-01 to the current season"
        title={
          <>
            Twenty-six seasons,
            <br className="hidden sm:block" /> read by a model
          </>
        }
        lede="Player and team statistics from every regular season since 2000, and machine-learning models built on them: who wins MVP, and who wins tonight's game."
      />

      <Section>
        <SectionHeading
          number="01"
          title="The MVP record"
          aside={
            <Link href="/mvp" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
              MVP Race <ArrowRightIcon className="size-3.5" />
            </Link>
          }
        />
        <Suspense fallback={<Skeleton className="h-20 w-full" />}>
          <MvpRecord />
        </Suspense>
      </Section>

      <Section>
        <SectionHeading
          number="02"
          title="The game model"
          aside={
            <Link href="/games" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
              This week&apos;s games <ArrowRightIcon className="size-3.5" />
            </Link>
          }
        />
        <Suspense fallback={<Skeleton className="h-28 w-full" />}>
          <GameModel />
        </Suspense>
      </Section>

      <Section>
        <SectionHeading number="03" title="In this almanac" />
        <ol className="border-t">
          {CONTENTS.map((item, index) => {
            const body = (
              <>
                <span className="tabular font-display text-2xl font-bold text-muted-foreground group-hover:text-brand">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span>
                  <span className="block font-display text-2xl leading-tight font-bold uppercase">{item.title}</span>
                  <span className="mt-0.5 block text-sm text-muted-foreground">{item.description}</span>
                </span>
                <span className={cn("eyebrow self-center text-right", item.href ? "text-brand" : "text-muted-foreground")}>
                  {item.href ? "Open →" : "In progress"}
                </span>
              </>
            );
            const layout = "grid grid-cols-[2.5rem_1fr_auto] gap-4 border-b py-4";
            return (
              <li key={item.title}>
                {item.href ? (
                  <Link href={item.href} className={cn(layout, "group transition-colors hover:bg-muted/40")}>
                    {body}
                  </Link>
                ) : (
                  <div className={cn(layout, "opacity-60")}>{body}</div>
                )}
              </li>
            );
          })}
        </ol>
      </Section>
    </>
  );
}

async function MvpRecord() {
  const overview = await getMvpOverview();
  return (
    <>
      <SeasonStrip results={overview.seasons} />
      <FigureRow className="mt-8">
        <Figure
          label="Seasons called correctly"
          value={ratio(overview.correct, overview.total)}
          detail={`${percent(overview.correct / overview.total)}, each predicted by a model that never saw the answer`}
          tone="brand"
        />
        <Figure label="MVP in the model's top 3" value={ratio(overview.top3, overview.total)} />
      </FigureRow>
    </>
  );
}

async function GameModel() {
  const meta = await getMeta();
  const model = meta.game_model;
  const live = meta.game_season;
  return (
    <>
      <FigureRow>
        <Figure label="Model" value={percent(model.accuracy)} tone="brand" />
        <Figure label="Elo ratings alone" value={percent(model.elo_baseline)} />
        <Figure label="Pick the better record" value={percent(model.record_baseline)} />
        <Figure label="Always pick the home team" value={percent(model.home_baseline)} />
      </FigureRow>
      <p className="mt-4 max-w-2xl font-serif text-[1.0625rem] leading-relaxed text-muted-foreground">
        Trained on {model.train_games.toLocaleString("en-US")} games from {model.train_first_season} to{" "}
        {model.train_last_season}, then tested on all {model.test_games.toLocaleString("en-US")} games of{" "}
        {model.test_season}, which it never saw. It weighs team strength, form, rest and travel, and the official
        injury report, with each player counted by what he is worth to his team: a star ruled out moves the line, a
        deep reserve does not.
        {live && live.games_played > 0 && (
          <>
            {" "}
            So far in {live.season} it has called {ratio(live.correct, live.games_played)} winners.
          </>
        )}
      </p>
    </>
  );
}
