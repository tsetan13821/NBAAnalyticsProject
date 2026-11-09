import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { StatTile, StatTileSkeleton } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getMeta } from "@/lib/api/client";
import { percent, ratio, seasonCount } from "@/lib/format";

const COMING_SOON = [
  { title: "Players", description: "Search 2,000 players, career profiles and side-by-side percentile comparisons." },
  { title: "Game predictor", description: "Win probability for any matchup from each team's record." },
  { title: "Franchises", description: "26 seasons of records, rosters and championships for all 30 teams." },
];

export default function HomePage() {
  return (
    <>
      <PageHeader
        eyebrow="2000-01 to 2025-26"
        title="Machine learning on 26 NBA seasons"
        description="Player and team data from NBA.com, an MVP model tested on every season it never saw, and a game win-probability model."
      />

      <Suspense fallback={<HeadlineSkeleton />}>
        <Headline />
      </Suspense>

      <h2 className="mt-12 mb-4 text-lg font-semibold tracking-tight">Explore</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/mvp" className="group rounded-xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
          <Card className="h-full ring-brand/40 transition-colors group-hover:bg-accent/60 group-hover:ring-brand">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                MVP Race
                <ArrowRightIcon className="size-4 text-brand transition-transform group-hover:translate-x-0.5" />
              </CardTitle>
              <CardDescription>
                Who the model picked each season, who actually won, and the full candidate field.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        {COMING_SOON.map(({ title, description }) => (
          <Card key={title} className="h-full opacity-70">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {title}
                <Badge variant="secondary">Soon</Badge>
              </CardTitle>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </>
  );
}

async function Headline() {
  const meta = await getMeta();
  const nextGame = meta.next_game_model;
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatTile
        label="MVP picks correct"
        value={ratio(meta.mvp_model.correct, meta.mvp_model.seasons)}
        detail={`${percent(meta.mvp_model.correct / meta.mvp_model.seasons)} of seasons, each predicted by a model that never saw it`}
        emphasis
      />
      <StatTile
        label="Game predictions correct"
        value={percent(nextGame.accuracy)}
        detail={`${nextGame.test_games.toLocaleString("en-US")} games in ${nextGame.test_season}. Always picking the home team: ${percent(nextGame.home_baseline)}; picking the better record: ${percent(nextGame.record_baseline)}`}
      />
      <StatTile
        label="Seasons"
        value={String(seasonCount(meta.first_season, meta.last_season))}
        detail={`${meta.first_season} to ${meta.last_season}`}
      />
    </div>
  );
}

function HeadlineSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatTileSkeleton />
      <StatTileSkeleton />
      <StatTileSkeleton />
    </div>
  );
}
