import { ArrowLeftIcon, ArrowRightIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { MvpRaceChart } from "@/components/charts/mvp-race-chart";
import { Section, SectionHeading } from "@/components/editorial";
import { CandidatesTable } from "@/components/mvp/candidates-table";
import { SeasonStrip } from "@/components/mvp/season-strip";
import { PageHeader } from "@/components/page-header";
import { PlayerAvatar } from "@/components/player-avatar";
import { SeasonPicker } from "@/components/season-picker";
import { TeamBadge } from "@/components/team-badge";
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
        className="eyebrow mb-6 inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-3.5" />
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
        eyebrow={era ? `${era.label} model · ${race.candidates.length} candidates` : undefined}
        title={`${season} MVP Race`}
        lede={
          race.correct
            ? `The model's first choice, ${pick.player.name}, won the award.`
            : `The model backed ${pick.player.name}. The award went to ${mvp?.player.name ?? "another player"}, its ${ordinal(race.actual_rank)} choice.`
        }
        actions={<SeasonPicker seasons={overview.seasons.map((s) => s.season)} current={season} href="/mvp/{season}" />}
      />

      <Section>
        <SectionHeading
          number="01"
          title={race.correct ? "The call" : "Pick against winner"}
          aside={
            <span className={cn("eyebrow", race.correct ? "text-hit" : "text-miss")}>
              {race.correct ? "Hit" : `Miss · MVP ranked ${ordinal(race.actual_rank)}`}
            </span>
          }
        />
        {race.correct || !mvp ? <PlayerLine label="Model pick and MVP" candidate={pick} winner /> : <TaleOfTheTape pick={pick} mvp={mvp} />}
      </Section>

      <Section>
        <SectionHeading number="02" title="Share of the model's score" />
        <p className="-mt-3 mb-4 text-sm text-muted-foreground">
          Each candidate&apos;s score as a share of the field. The real MVP is in{" "}
          <span className="font-medium text-brand">orange</span>.
        </p>
        <MvpRaceChart season={season} candidates={race.candidates} />
      </Section>

      <Section>
        <SectionHeading
          number="03"
          title="The field"
          aside={
            <Link href="/mvp/method#candidates" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
              Who qualifies <ArrowRightIcon className="size-3.5" />
            </Link>
          }
        />
        <p className="-mt-3 mb-4 text-sm text-muted-foreground">
          Per-game stats. The team column shows win percentage and conference seed.
        </p>
        <CandidatesTable candidates={race.candidates} />
      </Section>

      <Section>
        <SectionHeading number="04" title="Every season" />
        <SeasonStrip results={overview.seasons} current={season} />
      </Section>
    </>
  );
}

const TAPE_ROWS: {
  label: string;
  short: string;
  value: (c: MvpCandidate) => number;
  format: (n: number) => string;
}[] = [
  { label: "Points", short: "PTS", value: (c) => c.stats.pts_pg, format: stat },
  { label: "Rebounds", short: "REB", value: (c) => c.stats.reb_pg, format: stat },
  { label: "Assists", short: "AST", value: (c) => c.stats.ast_pg, format: stat },
  { label: "True shooting", short: "TS%", value: (c) => c.stats.ts_pct, format: percent },
  { label: "Team win %", short: "Win %", value: (c) => c.team_win_pct, format: percent },
  { label: "Model score", short: "Score", value: (c) => c.score_share, format: percent },
];

/** The model's pick and the real MVP side by side, with the larger number in each row marked. */
function TaleOfTheTape({ pick, mvp }: { pick: MvpCandidate; mvp: MvpCandidate }) {
  return (
    <div className="border-y">
      <div className="grid grid-cols-2 divide-x">
        <TapeHeader label="Model's pick" candidate={pick} />
        <TapeHeader label="Actual MVP" candidate={mvp} winner />
      </div>
      <table className="w-full border-t">
        <caption className="sr-only">
          {pick.player.name} against {mvp.player.name}
        </caption>
        <tbody>
          {TAPE_ROWS.map((row) => {
            const a = row.value(pick);
            const b = row.value(mvp);
            return (
              <tr key={row.label} className="border-b last:border-b-0">
                <td className={cn("tabular w-[38%] py-2 pr-4 text-right font-display text-2xl font-bold", a > b ? "text-foreground" : "text-muted-foreground")}>
                  {row.format(a)}
                </td>
                <th scope="row" className="eyebrow px-2 text-center font-semibold whitespace-nowrap text-muted-foreground">
                  <span className="sm:hidden" aria-hidden="true">{row.short}</span>
                  <span className="max-sm:sr-only">{row.label}</span>
                </th>
                <td className={cn("tabular w-[38%] py-2 pl-4 font-display text-2xl font-bold", b > a ? "text-brand" : "text-muted-foreground")}>
                  {row.format(b)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TapeHeader({ label, candidate, winner = false }: { label: string; candidate: MvpCandidate; winner?: boolean }) {
  return (
    <div className={cn("flex flex-col items-center gap-3 px-2 py-5 text-center", winner && "bg-paper")}>
      <span className={cn("eyebrow", winner ? "text-brand" : "text-muted-foreground")}>{label}</span>
      <PlayerAvatar player={candidate.player} size="lg" />
      <div className="min-w-0">
        <div className="font-display text-2xl leading-tight font-bold uppercase sm:text-3xl">{candidate.player.name}</div>
        <div className="mt-1.5 flex flex-wrap items-center justify-center gap-2 text-sm text-muted-foreground">
          <TeamBadge team={candidate.team} />
          <span className="hidden sm:inline">{candidate.team.name}</span>
          <span className="tabular">· Model #{candidate.rank}</span>
        </div>
      </div>
    </div>
  );
}

/** One player across the full width: used when the pick and the MVP are the same person. */
function PlayerLine({ label, candidate, winner = false }: { label: string; candidate: MvpCandidate; winner?: boolean }) {
  const stats = [
    { label: "PTS", value: stat(candidate.stats.pts_pg) },
    { label: "REB", value: stat(candidate.stats.reb_pg) },
    { label: "AST", value: stat(candidate.stats.ast_pg) },
    { label: "TS%", value: percent(candidate.stats.ts_pct) },
    { label: "Score", value: percent(candidate.score_share) },
  ];
  return (
    <div className={cn("grid gap-6 border-y py-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-center", winner && "bg-paper px-4 sm:px-6")}>
      <div className="flex items-center gap-5">
        <PlayerAvatar player={candidate.player} size="lg" />
        <div className="min-w-0">
          <span className="eyebrow text-brand">{label}</span>
          <div className="font-display text-3xl leading-tight font-bold uppercase sm:text-4xl">{candidate.player.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <TeamBadge team={candidate.team} />
            <span>{candidate.team.name}</span>
          </div>
        </div>
      </div>
      <dl className="grid grid-cols-5 gap-4 sm:gap-6">
        {stats.map(({ label: statLabel, value }) => (
          <div key={statLabel} className="flex flex-col">
            <dt className="eyebrow order-2 text-muted-foreground">{statLabel}</dt>
            <dd className="tabular order-1 font-display text-2xl font-bold sm:text-3xl">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SeasonSkeleton() {
  return (
    <>
      <div className="mb-10 flex flex-col gap-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-16 w-96 max-w-full" />
        <Skeleton className="h-5 w-[32rem] max-w-full" />
      </div>
      <Skeleton className="h-56 w-full" />
      <Skeleton className="mt-16 h-80 w-full" />
    </>
  );
}
