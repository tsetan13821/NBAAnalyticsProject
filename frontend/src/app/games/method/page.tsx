import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Decision, Figure, FigureRow, Section, SectionHeading } from "@/components/editorial";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { type GameModelDetails, getGameModel } from "@/lib/api/client";
import { percent } from "@/lib/format";
import { signedPoints } from "@/lib/games";

export const metadata: Metadata = {
  title: "How the game predictor works",
  description:
    "The inputs, player values, injury report, model and testing behind the NBA game predictor, with the decisions and their trade-offs.",
};

const CONTENTS = [
  { id: "question", title: "The question" },
  { id: "teams", title: "How good is each team" },
  { id: "players", title: "What each player is worth" },
  { id: "injuries", title: "Who plays tonight" },
  { id: "model", title: "The model" },
  { id: "testing", title: "Testing it honestly" },
  { id: "limitations", title: "Limitations" },
];

const MODEL_NAMES: Record<string, string> = {
  margin_ridge: "Margin model (used)",
  logistic: "Logistic regression",
  xgboost: "Gradient boosting (XGBoost)",
};

const GROUP_NAMES: Record<string, string> = {
  strength: "Team strength",
  home: "Home court",
  season: "Season so far and form",
  schedule: "Rest and travel",
  roster: "Rotation quality",
  availability: "Tonight's availability",
  "availability (who actually played)": "…if we knew who would play",
};

export default function GameMethodPage() {
  return (
    <>
      <PageHeader
        eyebrow="Methodology · Game predictor"
        title="How the model calls a game"
        lede="Every input behind a prediction, how the injury report becomes a number, and how the model was tested on seasons it never saw."
      />
      <Suspense fallback={<Skeleton className="h-[40rem] w-full" />}>
        <Method />
      </Suspense>
    </>
  );
}

async function Method() {
  const model = await getGameModel();
  const ev = model.evaluation;
  const coefficient = (name: string) => model.features.find((f) => f.name === name)?.coefficient ?? 0;

  return (
    <>
      <FigureRow className="mb-16">
        <Figure label={`Winners called, ${ev.test_season}`} value={percent(ev.held_out.accuracy)} detail="A season it never saw" tone="brand" />
        <Figure label="Pick the better record" value={percent(ev.baselines.better_record)} />
        <Figure label="Elo ratings alone" value={percent(ev.baselines.elo.accuracy)} />
        <Figure label="Margin error" value={`${ev.held_out.margin_mae.toFixed(1)} pts`} detail="Average miss on the final margin" />
      </FigureRow>

      <div className="grid gap-12 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <nav aria-label="Contents" className="hidden lg:block">
          <div className="sticky top-24">
            <p className="eyebrow mb-3 text-muted-foreground">Contents</p>
            <ol className="space-y-2 border-l pl-4 text-sm">
              {CONTENTS.map((item, index) => (
                <li key={item.id}>
                  <a href={`#${item.id}`} className="flex gap-2 text-muted-foreground hover:text-foreground">
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
                Before tip-off, how likely is each team to win, and by how much? The model may only use what was known
                at the time: results of earlier games, the schedule, and the league&apos;s official injury report. Every
                game since {ev.train_first_season} is rebuilt that way, one day at a time, so nothing from the future
                leaks into a prediction.
              </p>
            </div>
          </Section>

          <Section>
            <SectionHeading number="02" id="teams" title="How good is each team" />
            <div className="article">
              <p>
                <strong>Elo ratings</strong> carry a team&apos;s strength from game to game and season to season. A win
                moves a rating up by more when it was unexpected or lopsided, and each summer every rating keeps three
                quarters of its distance from average. One point of expected margin is 28 Elo points.
              </p>
              <p>
                <strong>Net rating so far</strong> (points scored minus allowed per 100 possessions) is pulled toward zero
                for a team that has played few games, and <strong>form</strong> is the same over the last ten games,
                recent ones weighted most. <strong>Rest and travel</strong> add the days since each team last played,
                back-to-backs and three games in four nights, the distance the away team flew, and time zones it crossed
                heading east.
              </p>
            </div>
            <Decision title="Elo and net rating, both">
              Elo knows last season and reacts to every result; net rating knows how a team is winning this season.
              Adding net rating and form to Elo improved the held-out season&apos;s log loss (see the table in
              section 06), and the model learns how much to trust each.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="03" id="players" title="What each player is worth" />
            <div className="article">
              <p>
                Every game, a player&apos;s box score becomes a <strong>Game Score</strong> (John Hollinger&apos;s one-number
                summary of points, shooting, rebounds, assists, steals, blocks, fouls and turnovers). His rate is Game
                Score per minute this season, pulled toward last season&apos;s rate until he has played about 400 minutes.
                His <strong>value</strong> is how far that rate is above a replacement player&apos;s (a deep reserve: the
                20th percentile of regular players) times the minutes he usually plays.
              </p>
              <p>
                A team can only play 240 minutes, so minutes go to its best players first. A deep bench adds nothing
                while the starters are healthy, and fills in when they are not: losing a star costs his value minus what
                his replacement brings, not his whole value.
              </p>
            </div>
            <Decision title="Game Score, not plus-minus">
              Plus-minus measures what a player&apos;s lineups did, and needs many games to settle. Game Score is noisy
              for defence, but it is ready after a few games and the same for every season. The weakness is real: a
              defensive specialist is undervalued.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="04" id="injuries" title="Who plays tonight" />
            <div className="article">
              <p>
                The league publishes an <strong>injury report</strong> before every game day, listing each player who
                may miss it as Out, Doubtful, Questionable or Probable. The model reads the 5 PM report (an earlier one
                for afternoon games) and turns each status into a chance of playing, measured from how often listed
                players really played in the training seasons:
              </p>
            </div>
            <dl className="my-6 grid grid-cols-2 border-y sm:grid-cols-5 sm:divide-x">
              {Object.entries(model.play_rates).map(([status, rate]) => (
                <div key={status} className="py-3 sm:px-4 sm:first:pl-0">
                  <dt className="eyebrow text-muted-foreground">{status}</dt>
                  <dd className="tabular font-display text-3xl font-bold">{percent(rate, 0)}</dd>
                </div>
              ))}
            </dl>
            <div className="article">
              <p>
                A player not on the report plays, unless he has been sitting out without being listed (out of the
                rotation). Adding up value times chance gives what each team can expect to field tonight.
              </p>
              <p>
                The input is that number <strong>minus what the team has fielded in its last ten games</strong>. A star
                out for two months barely moves the prediction: the team&apos;s Elo and form already show life without
                him. A star missing his first game counts in full. A star coming back counts as a boost.
              </p>
            </div>
            <Decision title="Change from recent, not raw value">
              Counting a long-term absence again would punish a team twice: once in its results, once on the report.
              Measuring the change from the lineups a team has actually used avoids that, and was worth more than any
              other player input in testing.
            </Decision>
          </Section>

          <Section>
            <SectionHeading number="05" id="model" title="The model" />
            <div className="article">
              <p>
                A ridge regression predicts the home team&apos;s <strong>margin</strong> from {model.features.length} inputs,
                each the home side minus the away side. The win chance is the probability that the real margin, spread
                around the prediction with a standard deviation of {model.spread.toFixed(1)} points, ends above zero.
                With a normal crowd the home team starts {signedPoints(model.intercept)} points up.
              </p>
            </div>
            <FeatureTable model={model} />
            <Decision title="A straight line, on purpose">
              Every prediction splits into points per input (&ldquo;home court +1.6, Elo gap +4.2, injuries −3.1&rdquo;),
              which is what a game page shows. Gradient boosting, given the same inputs, did no better on unseen games:
            </Decision>
            <ScoresTable rows={Object.entries(ev.models).map(([name, s]) => ({ name: MODEL_NAMES[name] ?? name, ...s }))} />
          </Section>

          <Section>
            <SectionHeading number="06" id="testing" title="Testing it honestly" />
            <div className="article">
              <p>
                The model trains on {ev.train_first_season} to {ev.train_last_season} ({ev.train_games.toLocaleString("en-US")}{" "}
                games) and is scored on all {ev.test_games.toLocaleString("en-US")} games of {ev.test_season}, which it
                never saw. Accuracy counts winners called; <strong>log loss</strong> punishes confident misses, so a
                model can&apos;t win it by being bold (lower is better).
              </p>
              <h3>Each input, added in turn</h3>
            </div>
            <ScoresTable rows={ev.ablation.map((row) => ({ name: GROUP_NAMES[row.added] ?? row.added, ...row }))} first="Inputs so far" />
            <div className="article">
              <p>
                The last row is the same model told who really played, which nobody knows before tip-off: the gap to the
                row above is what the uncertainty of the injury report costs.
              </p>
              <h3>Season by season</h3>
              <p>Trained on every earlier season each time:</p>
            </div>
            <div className="overflow-x-auto">
              <table className="my-4 w-full min-w-[28rem] text-sm">
                <thead>
                  <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
                    <th scope="col" className="py-2 pr-4 font-semibold">Season</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Model</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Elo alone</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Better record</th>
                    <th scope="col" className="py-2 text-right font-semibold">Home team</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.walk_forward.map((row) => (
                    <tr key={row.season} className="border-b">
                      <td className="tabular py-2 pr-4 font-medium">{row.season}</td>
                      <td className="tabular py-2 pr-4 text-right font-semibold">{percent(row.accuracy)}</td>
                      <td className="tabular py-2 pr-4 text-right">{percent(row.baselines.elo.accuracy)}</td>
                      <td className="tabular py-2 pr-4 text-right">{percent(row.baselines.better_record)}</td>
                      <td className="tabular py-2 text-right">{percent(row.baselines.home_team)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="article">
              <h3>Are its chances honest?</h3>
              <p>Games of {ev.test_season} grouped by the favourite&apos;s predicted chance, against how often it won:</p>
            </div>
            <div className="overflow-x-auto">
              <table className="my-4 w-full min-w-[24rem] text-sm">
                <thead>
                  <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
                    <th scope="col" className="py-2 pr-4 font-semibold">Predicted</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Games</th>
                    <th scope="col" className="py-2 text-right font-semibold">Favourite won</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.calibration.map((bin) => (
                    <tr key={bin.low} className="border-b">
                      <td className="tabular py-2 pr-4">{percent(bin.predicted, 0)}</td>
                      <td className="tabular py-2 pr-4 text-right">{bin.games}</td>
                      <td className="tabular py-2 text-right font-semibold">{percent(bin.actual, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="article">
              <p>
                The deployed model is then refit on every season through {ev.test_season} ({model.trained_on}), and its
                record on the season in progress is on the <Link href="/games">game predictor</Link> page.
              </p>
            </div>
          </Section>

          <Section>
            <SectionHeading number="07" id="limitations" title="Limitations" />
            <div className="article">
              <ul>
                <li>
                  <strong>Game Score undervalues defence.</strong> A stopper who doesn&apos;t score looks replaceable.
                </li>
                <li>
                  <strong>The report is a snapshot.</strong> Late scratches and rest days announced after it are missed;
                  a Questionable player plays about {percent(model.play_rates.Questionable ?? 0.5, 0)} of the time, and the
                  model can only average.
                </li>
                <li>
                  <strong>Games further ahead</strong> carry each player&apos;s latest Out or Doubtful status forward,
                  which is right for long injuries and wrong for one-game absences.
                </li>
                <li>
                  <strong>No matchups.</strong> Inputs are team totals; a team that struggles against a particular style
                  is invisible to the model.
                </li>
                <li>
                  <strong>Basketball is noisy.</strong> Even a perfect model misses about three games in ten. A typical
                  real margin lands {Math.round(model.spread)} points from the prediction.
                </li>
              </ul>
              <p>
                Rest and travel weights such as a home back-to-back ({signedPoints(coefficient("HOME_B2B"))} points)
                are learned from the data, not set by hand.
              </p>
            </div>
          </Section>
        </article>
      </div>
    </>
  );
}

function FeatureTable({ model }: { model: GameModelDetails }) {
  return (
    <div className="overflow-x-auto">
      <table className="my-6 w-full min-w-[32rem] text-sm">
        <thead>
          <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-semibold">Input</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Group</th>
            <th scope="col" className="py-2 text-right font-semibold" title="Points of home margin per unit of the input">
              Weight
            </th>
          </tr>
        </thead>
        <tbody>
          {model.features.map((f) => (
            <tr key={f.name} className="border-b align-top">
              <td className="py-2 pr-4">
                <span className="font-medium">{f.label}</span>
                {f.description && <span className="block text-xs text-muted-foreground">{f.description}</span>}
              </td>
              <td className="py-2 pr-4 text-muted-foreground">{GROUP_NAMES[f.group] ?? f.group}</td>
              <td className="tabular py-2 text-right">{f.coefficient.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScoresTable({
  rows,
  first = "Model",
}: {
  rows: { name: string; accuracy: number; log_loss: number; brier: number }[];
  first?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="my-6 w-full min-w-[28rem] text-sm">
        <thead>
          <tr className="eyebrow border-b-2 border-foreground text-left text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-semibold">{first}</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Accuracy</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Log loss</th>
            <th scope="col" className="py-2 text-right font-semibold">Brier</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} className="border-b">
              <td className="py-2 pr-4">{row.name}</td>
              <td className="tabular py-2 pr-4 text-right">{percent(row.accuracy)}</td>
              <td className="tabular py-2 pr-4 text-right">{row.log_loss.toFixed(4)}</td>
              <td className="tabular py-2 text-right">{row.brier.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
