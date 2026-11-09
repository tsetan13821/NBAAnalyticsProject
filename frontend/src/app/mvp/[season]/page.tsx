import { ArrowLeftIcon, TrophyIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { MvpRaceChart } from "@/components/charts/mvp-race-chart";
import { CandidatesTable } from "@/components/mvp/candidates-table";
import { SeasonPicker } from "@/components/mvp/season-picker";
import { VerdictBadge } from "@/components/mvp/verdict-badge";
import { PageHeader } from "@/components/page-header";
import { PlayerAvatar } from "@/components/player-avatar";
import { TeamBadge } from "@/components/team-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getMvpOverview, getMvpRace, type MvpCandidate } from "@/lib/api/client";
import { isSeason, ordinal, percent, stat } from "@/lib/format";
import { cn } from "@/lib/utils";

export async function generateMetadata({ params }: PageProps<"/mvp/[season]">): Promise<Metadata> {
  const { season } = await params;
  return { title: `${season} MVP Race`, description: `The model's ranking of the ${season} NBA MVP candidates.` };
}

export default function MvpSeasonPage({ params }: PageProps<"/mvp/[season]">) {
  return (
    <>
      <Link
        href="/mvp"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" />
        All seasons
      </Link>
      {/* params is awaited inside the boundary, so the page shell can be served before the season is known. */}
      <Suspense fallback={<SeasonSkeleton />}>
        <SeasonRace params={params} />
      </Suspense>
    </>
  );
}

async function SeasonRace({ params }: Pick<PageProps<"/mvp/[season]">, "params">) {
  const { season } = await params;
  if (!isSeason(season)) notFound();

  const [race, overview] = await Promise.all([getMvpRace(season), getMvpOverview()]);
  if (!race) notFound();

  const era = overview.eras.find((e) => e.era === race.era);
  const pick = race.candidates[0];
  const mvp = race.candidates.find((c) => c.is_mvp);

  return (
    <>
      <PageHeader
        eyebrow={era ? `${era.label} model` : undefined}
        title={`${season} MVP Race`}
        description={
          race.correct
            ? `The model's top pick won the award.`
            : `The model's top pick didn't win. The real MVP was its ${ordinal(race.actual_rank)} choice.`
        }
        actions={<SeasonPicker seasons={overview.seasons.map((s) => s.season)} current={season} />}
      />

      <div className={cn("grid gap-4", !race.correct && "md:grid-cols-2")}>
        <HeadlinePlayer
          title={race.correct ? "Model pick and MVP" : "Model pick"}
          candidate={pick}
          badge={<VerdictBadge correct={race.correct} actualRank={race.actual_rank} />}
          highlight={race.correct}
        />
        {!race.correct && mvp && <HeadlinePlayer title="Actual MVP" candidate={mvp} highlight />}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Share of the model&apos;s score</CardTitle>
          <CardDescription>
            Each candidate&apos;s score as a share of the field. The real MVP is in <span className="text-brand">orange</span>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MvpRaceChart season={season} candidates={race.candidates} />
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>All {race.candidates.length} candidates</CardTitle>
          <CardDescription>Per-game stats; team column shows win % and conference seed.</CardDescription>
        </CardHeader>
        <CardContent>
          <CandidatesTable candidates={race.candidates} />
        </CardContent>
      </Card>
    </>
  );
}

function HeadlinePlayer({
  title,
  candidate,
  badge,
  highlight = false,
}: {
  title: string;
  candidate: MvpCandidate;
  badge?: React.ReactNode;
  highlight?: boolean;
}) {
  const stats = [
    { label: "PTS", value: stat(candidate.stats.pts_pg) },
    { label: "REB", value: stat(candidate.stats.reb_pg) },
    { label: "AST", value: stat(candidate.stats.ast_pg) },
    { label: "TS%", value: percent(candidate.stats.ts_pct) },
  ];
  return (
    <Card className={cn(highlight && "ring-brand/50")}>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {highlight && <TrophyIcon className="size-3.5 text-brand" aria-hidden="true" />}
            {title}
          </span>
          {badge}
        </div>
        <div className="flex items-center gap-4">
          <PlayerAvatar player={candidate.player} size="lg" />
          <div className="min-w-0">
            <div className="truncate text-xl font-semibold tracking-tight">{candidate.player.name}</div>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <TeamBadge team={candidate.team} />
              <span>{candidate.team.name}</span>
            </div>
            <div className="tabular mt-1 text-sm text-muted-foreground">
              Model rank {candidate.rank} · {percent(candidate.score_share)} of score
            </div>
          </div>
        </div>
        <dl className="grid grid-cols-4 gap-2 border-t pt-4">
          {stats.map(({ label, value }) => (
            <div key={label}>
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="tabular text-lg font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function SeasonSkeleton() {
  return (
    <>
      <div className="mb-8 flex flex-col gap-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-44 w-full rounded-xl" />
      <Skeleton className="mt-6 h-80 w-full rounded-xl" />
    </>
  );
}
