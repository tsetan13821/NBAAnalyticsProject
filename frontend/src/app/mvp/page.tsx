import type { Metadata } from "next";
import { Suspense } from "react";

import { SeasonResultCard, SeasonResultCardSkeleton } from "@/components/mvp/season-result-card";
import { PageHeader } from "@/components/page-header";
import { StatTile, StatTileSkeleton } from "@/components/stat-tile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getMvpOverview } from "@/lib/api/client";
import { percent, ratio } from "@/lib/format";

export const metadata: Metadata = {
  title: "MVP Race",
  description: "How well a machine-learning model picks the NBA MVP, season by season since 2000-01.",
};

export default function MvpPage() {
  return (
    <>
      <PageHeader
        eyebrow="MVP model"
        title="Can a model pick the MVP?"
        description="An XGBoost classifier ranks each season's MVP candidates. Every season is predicted by a model trained only on the other seasons, so it never sees the answer."
      />
      <Suspense fallback={<OverviewSkeleton />}>
        <Overview />
      </Suspense>
      <HowItWorks />
    </>
  );
}

async function Overview() {
  const overview = await getMvpOverview();
  const eras = overview.eras.toSorted((a, b) => b.era - a.era); // newest era first
  const [modern, early] = eras;
  const newestFirst = overview.seasons.toReversed();

  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="Correct picks"
          value={ratio(overview.correct, overview.total)}
          detail={`${percent(overview.correct / overview.total)} of seasons`}
          emphasis
        />
        <StatTile
          label="MVP in model's top 3"
          value={ratio(overview.top3, overview.total)}
          detail={percent(overview.top3 / overview.total)}
        />
        <StatTile label={modern.label} value={ratio(modern.correct, modern.seasons)} detail="Efficiency and impact features" />
        <StatTile label={early.label} value={ratio(early.correct, early.seasons)} detail="Box-score features" />
      </div>

      {eras.map((era) => (
        <section key={era.era} className="mt-10">
          <h2 className="mb-4 flex items-baseline gap-3 text-lg font-semibold tracking-tight">
            {era.label}
            <span className="tabular text-sm font-normal text-muted-foreground">
              {ratio(era.correct, era.seasons)} correct
            </span>
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {newestFirst
              .filter((result) => result.era === era.era)
              .map((result) => (
                <SeasonResultCard key={result.season} result={result} />
              ))}
          </div>
        </section>
      ))}
    </>
  );
}

function OverviewSkeleton() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <StatTileSkeleton key={i} />
        ))}
      </div>
      <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => (
          <SeasonResultCardSkeleton key={i} />
        ))}
      </div>
    </>
  );
}

const STEPS = [
  {
    title: "Candidates",
    body: "Players with at least 50 games on teams that won at least 55% of their games. Players on 55–65% teams also need elite usage and impact. Low-usage role players are filtered out.",
  },
  {
    title: "Two eras, two feature sets",
    body: "2000-01 to 2007-08 uses box-score stats (points, rebounds, assists, steals + blocks) and team seed. From 2008-09 the model uses efficiency and impact: true shooting, offensive load, PIE, an on/off proxy, defensive rating and games played. Every stat is compared within its own season.",
  },
  {
    title: "Tested on unseen seasons",
    body: "Leave-one-season-out validation: to predict a season, the model is retrained on every other season of its era. The candidate with the highest score is the pick.",
  },
];

function HowItWorks() {
  return (
    <section className="mt-12">
      <h2 className="mb-4 text-lg font-semibold tracking-tight">How it works</h2>
      <div className="grid gap-4 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <Card key={step.title} size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="tabular flex size-6 items-center justify-center rounded-full bg-brand/15 text-xs text-brand">
                  {index + 1}
                </span>
                {step.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground">{step.body}</CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
