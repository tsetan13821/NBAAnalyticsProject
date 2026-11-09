import { ArrowRightIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { SeasonLedger } from "@/components/mvp/season-ledger";
import { SeasonStrip } from "@/components/mvp/season-strip";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { CANDIDATE_FUNNEL } from "@/content/mvp-method";
import { getMvpOverview } from "@/lib/api/client";
import { percent, ratio } from "@/lib/format";

export const metadata: Metadata = {
  title: "MVP Race",
  description: "How well a machine-learning model picks the NBA MVP, season by season since 2000-01.",
};

const IN_BRIEF = [
  {
    title: "Narrow the field",
    body: `Six basketball rules (team record, games played, usage, impact, offensive output) cut ${CANDIDATE_FUNNEL[0].count.toLocaleString("en-US")} player-seasons to ${CANDIDATE_FUNNEL[CANDIDATE_FUNNEL.length - 1].count} candidates. Every real MVP survives.`,
  },
  {
    title: "Compare within the season",
    body: "Each stat becomes a z-score against that season's other candidates, so different scoring eras compare fairly.",
  },
  {
    title: "Two eras, two models",
    body: "2000-01 to 2007-08 is judged on volume and record; 2008-09 onward on efficiency and impact. Each is an XGBoost classifier.",
  },
  {
    title: "Never see the answer",
    body: "Each season is predicted by a model trained on the other seasons of its era, never on the season itself.",
  },
];

export default function MvpPage() {
  return (
    <>
      <PageHeader
        eyebrow="MVP model · 2000-01 to 2025-26"
        title="Can a model call the MVP?"
        lede="A model ranks each season's contenders from their regular-season numbers. Every season is predicted by a version of the model that never saw who won."
      />

      <Suspense fallback={<OverviewSkeleton />}>
        <Overview />
      </Suspense>

      <Section>
        <SectionHeading
          number="02"
          title="The method in brief"
          aside={
            <Link href="/mvp/method" className="eyebrow inline-flex items-center gap-1.5 text-brand hover:underline">
              Full methodology <ArrowRightIcon className="size-3.5" />
            </Link>
          }
        />
        <ol className="grid gap-px border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {IN_BRIEF.map((step, index) => (
            <li key={step.title} className="bg-background p-5">
              <span className="tabular font-display text-4xl leading-none font-bold text-brand">{index + 1}</span>
              <h3 className="mt-3 font-display text-xl leading-tight font-bold uppercase">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Suspense fallback={<Skeleton className="mt-16 h-96 w-full" />}>
        <Ledger />
      </Suspense>
    </>
  );
}

async function Overview() {
  const overview = await getMvpOverview();
  const [modern, early] = overview.eras.toSorted((a, b) => b.era - a.era);
  return (
    <Section>
      <SectionHeading number="01" title="Season by season" aside="Select a season to see the full race" />
      <SeasonStrip results={overview.seasons} />
      <FigureRow className="mt-8">
        <Figure
          label="Picked the MVP"
          value={ratio(overview.correct, overview.total)}
          detail={`${percent(overview.correct / overview.total)} of seasons`}
          tone="brand"
        />
        <Figure label="MVP in its top 3" value={ratio(overview.top3, overview.total)} detail={percent(overview.top3 / overview.total)} />
        <Figure label={modern.label} value={ratio(modern.correct, modern.seasons)} detail="Efficiency and impact model" />
        <Figure label={early.label} value={ratio(early.correct, early.seasons)} detail="Volume and record model" />
      </FigureRow>
    </Section>
  );
}

async function Ledger() {
  const overview = await getMvpOverview();
  return (
    <Section>
      <SectionHeading number="03" title="The ledger" aside="Newest first" />
      <SeasonLedger results={overview.seasons} eras={overview.eras} />
    </Section>
  );
}

function OverviewSkeleton() {
  return (
    <Section>
      <Skeleton className="mb-6 h-10 w-full" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="mt-8 h-28 w-full" />
    </Section>
  );
}
