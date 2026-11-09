import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Decision, Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { CandidateFunnel } from "@/components/mvp/candidate-funnel";
import { ValidationDiagram } from "@/components/mvp/validation-diagram";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CANDIDATE_FUNNEL,
  CANDIDATES_PER_ERA,
  CANDIDATES_PER_SEASON,
  ERA_FEATURES,
  MODEL_SETTINGS,
} from "@/content/mvp-method";
import { getMvpOverview } from "@/lib/api/client";
import { ordinal, percent, ratio } from "@/lib/format";

export const metadata: Metadata = {
  title: "How the MVP model works",
  description:
    "The rules, features, model settings and validation behind the NBA MVP predictor, with the decisions and their trade-offs.",
};

const CONTENTS = [
  { id: "question", title: "The question" },
  { id: "candidates", title: "Who counts as a candidate" },
  { id: "features", title: "Comparing players fairly" },
  { id: "eras", title: "Two eras, two models" },
  { id: "model", title: "The model" },
  { id: "validation", title: "Testing it honestly" },
  { id: "results", title: "Results" },
  { id: "limitations", title: "Limitations" },
];

const NUMBER = new Intl.NumberFormat("en-US");

export default function MethodPage() {
  const funnelStart = CANDIDATE_FUNNEL[0].count;
  const funnelEnd = CANDIDATE_FUNNEL[CANDIDATE_FUNNEL.length - 1].count;

  return (
    <>
      <PageHeader
        eyebrow="Methodology · MVP model"
        title="How the model picks an MVP"
        lede="Every rule, feature and setting behind the MVP predictor: what it does, why it was chosen, and where it falls short."
      />

      <FigureRow className="mb-16">
        <Figure label="Player-seasons" value={NUMBER.format(funnelStart)} detail="2000-01 to 2025-26" />
        <Figure label="Candidates after the rules" value={funnelEnd} detail={`${CANDIDATES_PER_SEASON.median} a season on average`} />
        <Figure label="Real MVPs kept" value="26/26" detail="No winner is filtered out" />
        <Suspense fallback={<Figure label="Picked correctly" value="—" />}>
          <AccuracyFigure />
        </Suspense>
      </FigureRow>

      <div className="grid gap-12 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <nav aria-label="Contents" className="hidden lg:block">
          <div className="sticky top-24">
            <p className="eyebrow mb-3 text-muted-foreground">Contents</p>
            <ol className="space-y-2 border-l pl-4 text-sm">
              {CONTENTS.map((item, index) => (
                <li key={item.id}>
                  <a href={`#${item.id}`} className="group flex gap-2 text-muted-foreground hover:text-foreground">
                    <span className="tabular font-display font-semibold text-brand">{String(index + 1).padStart(2, "0")}</span>
                    {item.title}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </nav>

        <article className="min-w-0">
          <Section>
            <SectionHeading number="01" id="question" title="The question" />
            <div className="article">
              <p>
                Each season the MVP award goes to one player, chosen by a panel of about 100 media voters. The model
                tries to name that player from the regular-season numbers alone.
              </p>
              <p>
                It treats each season as a ranking problem. Every candidate gets a score for &ldquo;looks like an
                MVP&rdquo;, the candidates are sorted by score, and the top one is the model&apos;s pick. The pick is
                right when it matches the real winner.
              </p>
            </div>
            <Decision title="Predict the winner, not the vote">
              NBA.com publishes stats but not voting results, so there are no vote shares to learn from. With one
              label per season (MVP or not), the honest framing is a classifier whose scores are used to rank the
              field. Vote shares from Basketball Reference would allow a richer model; see{" "}
              <a href="#limitations" className="text-foreground underline underline-offset-4">limitations</a>.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="02" id="candidates" title="Who counts as a candidate" />
            <div className="article mb-8">
              <p>
                Most players have no chance of winning. Before any machine learning, six basketball rules cut{" "}
                {NUMBER.format(funnelStart)} player-seasons down to {funnelEnd} candidates, between{" "}
                {CANDIDATES_PER_SEASON.min} and {CANDIDATES_PER_SEASON.max} a season. Each rule is checked against
                every MVP since 2000, and all 26 pass with room to spare.
              </p>
            </div>
            <CandidateFunnel steps={CANDIDATE_FUNNEL} />
            <p className="mt-3 text-sm text-muted-foreground">
              Bars use a log scale. PIE (Player Impact Estimate) is NBA.com&apos;s share of all game events a player
              is responsible for; usage is the share of team possessions a player finishes while on the court.
            </p>
            <Decision title="Filter with basketball knowledge first">
              Without filters the data has one MVP for every 400 player-seasons, and a model mostly learns to say
              &ldquo;not MVP&rdquo;. The rules remove the obvious non-contenders, so the model spends its capacity on
              the hard part: separating the MVP from the other stars. The cost is hindsight, because the thresholds
              were set knowing who won. That makes the accuracy below somewhat optimistic.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="03" id="features" title="Comparing players fairly" />
            <div className="article">
              <p>
                Raw numbers aren&apos;t comparable across seasons. Teams averaged about 93 points a game in 2003-04
                and about 114 in 2023-24, so 28 points a game means different things in each. Every feature is
                therefore turned into a <strong>z-score within its own season</strong>: how many standard deviations
                a player is above or below that season&apos;s other candidates.
              </p>
              <p>Three features are built from the raw stats:</p>
            </div>
            <dl className="mt-6 grid gap-px border bg-border sm:grid-cols-3">
              {[
                { name: "Offensive load", formula: "usage % + assist %", body: "How much of the offense runs through the player, as a scorer or a passer." },
                { name: "Stocks", formula: "steals + blocks", body: "A simple measure of defensive activity." },
                { name: "On/off proxy", formula: "net rating − team margin", body: "How much better the team is with the player on the court than its average." },
              ].map((item) => (
                <div key={item.name} className="bg-background p-4">
                  <dt className="font-display text-lg font-bold uppercase">{item.name}</dt>
                  <dd className="mt-1">
                    <span className="formula">{item.formula}</span>
                  </dd>
                  <dd className="mt-2 text-sm text-muted-foreground">{item.body}</dd>
                </div>
              ))}
            </dl>
            <div className="article mt-6">
              <p>
                Team success enters twice. <strong>Team record rank</strong> is where the player&apos;s team ranks by
                win % among that season&apos;s candidates. <strong>Top-2 record</strong> is a flag for the two best,
                because MVPs almost always come from one of the league&apos;s best teams.
              </p>
            </div>
            <Decision title="Compare players within their season">
              Z-scores make a stat mean &ldquo;how unusual this was that year&rdquo;, which removes changes in pace
              and scoring across 26 seasons. They&apos;re computed among the candidates rather than the whole league,
              so they measure the gap between contenders, which is the comparison voters actually make.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="04" id="eras" title="Two eras, two models" />
            <div className="article mb-8">
              <p>
                What wins MVP has changed. In the 2000s voters rewarded scoring volume, rebounds and the best record.
                From around 2008 they leaned on efficiency and impact. A single model blurred the two, so there are
                two, each trained only on its own seasons and each with its own feature set.
              </p>
            </div>
            <div className="grid gap-px border bg-border md:grid-cols-2">
              {ERA_FEATURES.map((era) => (
                <div key={era.era} className="bg-background p-5">
                  <p className="eyebrow text-brand">Era {era.era} · {era.seasons} seasons · {CANDIDATES_PER_ERA[era.era]} candidates</p>
                  <h3 className="mt-1 font-display text-2xl font-bold uppercase">{era.label}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{era.summary}</p>
                  <ul className="mt-4 divide-y border-y">
                    {era.features.map((feature) => (
                      <li key={feature.name} className="flex justify-between gap-4 py-1.5 text-sm">
                        <span className="font-medium">{feature.name}</span>
                        <span className="text-right text-muted-foreground">{feature.detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <Decision title="Split at 2008-09, by judgement">
              The boundary is a judgement call based on how MVP debates shifted toward efficiency and impact
              stats, not something the model learned. The 2000-01 to 2007-08 model also uses a &ldquo;won last
              season&rdquo; flag for voter fatigue; the later model doesn&apos;t. The trade-off: the whole early era has
              only {CANDIDATES_PER_ERA[1]} candidates and 8 winners, and each test trains on 7 of those seasons.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="05" id="model" title="The model" />
            <table className="w-full text-sm">
              <tbody>
                {MODEL_SETTINGS.map((setting) => (
                  <tr key={setting.name} className="border-b first:border-t-2 first:border-t-foreground">
                    <th scope="row" className="eyebrow py-3 pr-4 text-left align-top text-muted-foreground">
                      {setting.name}
                    </th>
                    <td className="py-3 pr-4 align-top font-display text-xl font-bold whitespace-nowrap">{setting.value}</td>
                    <td className="py-3 align-top text-muted-foreground">{setting.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Decision title="Small, shallow and reweighted">
              With so few rows, a deep model would memorise individual seasons. Shallow trees can only learn broad
              patterns such as &ldquo;efficient, high-load player on a top-2 team&rdquo;, which is what transfers to
              a season the model hasn&apos;t seen.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="06" id="validation" title="Testing it honestly" />
            <div className="article mb-8">
              <p>
                A model that has seen a season&apos;s answer can&apos;t be tested on it. So each season is predicted
                by a model trained on <strong>every other season of the same era</strong> and never on the season
                itself. That&apos;s repeated 26 times, once per season. This is leave-one-season-out
                cross-validation.
              </p>
            </div>
            <ValidationDiagram />
            <div className="article mt-8">
              <p>
                The pages show each candidate&apos;s <strong>share of the model&apos;s score</strong>: the raw score
                divided by the season&apos;s total. It shows how one-sided the race was, but it isn&apos;t a
                calibrated probability of winning.
              </p>
            </div>
            <Decision title="Leave one season out, not a time split">
              With 26 seasons, a strict &ldquo;train on the past, test on the future&rdquo; split would leave the
              early seasons with almost no training data. Leaving one season out tests every season, at the cost of
              letting later seasons inform earlier predictions.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="07" id="results" title="Results" />
            <Suspense fallback={<Skeleton className="h-64 w-full" />}>
              <Results />
            </Suspense>
          </Section>

          <Section>
            <SectionHeading number="08" id="limitations" title="Limitations" />
            <ul className="article list-none space-y-4">
              <li>
                <strong>Hindsight.</strong> The candidate rules and the era split were chosen knowing who won, so the
                accuracy is an upper bound. The true test is predicting a season before the vote.
              </li>
              <li>
                <strong>Very little data.</strong> There are 26 winners in total, and the early model learns from 7
                seasons at a time. One unusual season can change what the model learns.
              </li>
              <li>
                <strong>No votes, no narrative.</strong> Voters weigh storylines, team turnarounds and fatigue that
                aren&apos;t in a box score. Steve Nash&apos;s 2005-06 award, ranked 8th by the model, is the clearest
                case.
              </li>
              <li>
                <strong>Scores are relative.</strong> Z-scores depend on who else passed the filters, so a player&apos;s
                score can change if the candidate pool changes.
              </li>
              <li>
                <strong>Rough proxies.</strong> The on/off proxy mixes a per-100-possession rating with a per-game
                margin; true on/off data would be better.
              </li>
            </ul>
            <div className="article mt-6">
              <p>
                <strong>Next:</strong> adding MVP vote shares from Basketball Reference would let the model learn the
                whole order of the vote rather than just the winner, and use every finalist as a training signal.
              </p>
            </div>
          </Section>
        </article>
      </div>
    </>
  );
}

async function AccuracyFigure() {
  const overview = await getMvpOverview();
  return (
    <Figure
      label="Picked correctly"
      value={ratio(overview.correct, overview.total)}
      detail={`${percent(overview.correct / overview.total)} of seasons`}
      tone="brand"
    />
  );
}

async function Results() {
  const overview = await getMvpOverview();
  const misses = overview.seasons.filter((s) => !s.correct);
  const eras = overview.eras.toSorted((a, b) => b.era - a.era);

  return (
    <>
      <div className="article mb-8">
        <p>
          The model named the MVP in <strong>{ratio(overview.correct, overview.total)}</strong> seasons, and the real
          winner was in its top three in <strong>{ratio(overview.top3, overview.total)}</strong>. Accuracy is much
          higher after 2008 ({eras.map((e) => `${e.label}: ${ratio(e.correct, e.seasons)}`).join("; ")}), partly
          because that model has more than twice as much data.
        </p>
      </div>
      <p className="eyebrow mb-2 text-muted-foreground">Every miss</p>
      <ul className="border-t-2 border-foreground">
        {misses.map((miss) => (
          <li key={miss.season} className="grid grid-cols-[4.5rem_1fr] items-baseline gap-x-4 border-b py-2.5 text-sm sm:grid-cols-[5rem_1fr_1fr_auto]">
            <Link href={`/mvp/${miss.season}`} className="tabular font-display text-lg font-bold hover:text-brand">
              {miss.season}
            </Link>
            <span>
              <span className="text-muted-foreground">Picked </span>
              {miss.predicted.name}
            </span>
            <span className="col-start-2 sm:col-start-auto">
              <span className="text-muted-foreground">Winner </span>
              {miss.actual.name}
            </span>
            <span className="eyebrow col-start-2 text-miss sm:col-start-auto sm:text-right">
              Ranked {ordinal(miss.actual_rank)}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
