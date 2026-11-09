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
  { title: "Players", description: "Search 2,000 players, career profiles and percentile comparisons." },
  { title: "Game predictor", description: "Win probability for any matchup from each team's record." },
  { title: "Franchises", description: "Records, rosters and championships for all 30 teams." },
];

export default function HomePage() {
  return (
    <>
      <PageHeader
        eyebrow="NBA.com data · 2000-01 to 2025-26"
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
        <SectionHeading number="02" title="The game model" />
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
  const model = meta.next_game_model;
  return (
    <>
      <FigureRow>
        <Figure label="Model" value={percent(model.accuracy)} tone="brand" />
        <Figure label="Always pick the home team" value={percent(model.home_baseline)} />
        <Figure label="Pick the better record" value={percent(model.record_baseline)} />
      </FigureRow>
      <p className="mt-4 max-w-2xl font-serif text-[1.0625rem] leading-relaxed text-muted-foreground">
        Share of {model.test_games.toLocaleString("en-US")} games in {model.test_season} called correctly, from each
        team&apos;s record before tip-off. The model clearly beats &ldquo;home team wins&rdquo; but falls just
        short of simply backing the team with the better record, an honest sign of how much a record alone can tell
        you.
      </p>
    </>
  );
}
