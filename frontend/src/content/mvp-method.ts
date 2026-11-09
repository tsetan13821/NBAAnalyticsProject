/**
 * Facts about the MVP model, mirrored from src/models/mvp_prediction.py.
 *
 * The funnel counts come from applying the candidate filters, in order, to data/processed/mvp_data.csv
 * (10,617 player-seasons, 2000-01 to 2025-26). They describe historical data and only change if the
 * pipeline's filters or source data change; if that happens, recompute them and update this file.
 */

export type FunnelStep = {
  count: number;
  rule: string;
  why: string;
};

export const CANDIDATE_FUNNEL: FunnelStep[] = [
  {
    count: 10_617,
    rule: "Every player-season",
    why: "Regular-season totals and advanced stats for everyone who played, about 408 players a season.",
  },
  {
    count: 4_195,
    rule: "Team won at least 55% of its games",
    why: "MVPs come from winning teams. The lowest team record of any MVP since 2000 is .573 (Russell Westbrook, 2016-17).",
  },
  {
    count: 1_716,
    rule: "On a 55–65% team: PIE ≥ 18% and usage ≥ 28%",
    why: "The “Westbrook rule”. A player on a merely good team needs a historically big individual season to stay in the race. Teams above 65% skip this check.",
  },
  {
    count: 1_318,
    rule: "Played at least 50 games",
    why: "Availability. The fewest games by an MVP in this period is 62.",
  },
  {
    count: 319,
    rule: "Usage ≥ 18% and PIE ≥ 12%",
    why: "Removes role players on great teams. Every MVP had usage of at least 20.1% and PIE of at least 14.5%.",
  },
  {
    count: 285,
    rule: "Points + 2 × assists ≥ 1,200 (season totals)",
    why: "MVPs create a lot of offense. The lowest MVP total on this measure is 2,442.",
  },
];

export const CANDIDATES_PER_SEASON = { min: 7, median: 11, max: 17 };
export const CANDIDATES_PER_ERA = { 1: 80, 2: 205 } as const;

export type Feature = { name: string; detail: string };

export const ERA_FEATURES: { era: 1 | 2; label: string; seasons: number; summary: string; features: Feature[] }[] = [
  {
    era: 1,
    label: "2000-01 to 2007-08",
    seasons: 8,
    summary: "Volume and winning: the box score and the standings.",
    features: [
      { name: "Points", detail: "season total, z-score" },
      { name: "Rebounds", detail: "season total, z-score" },
      { name: "Assists", detail: "season total, z-score" },
      { name: "Steals + blocks", detail: "season total, z-score" },
      { name: "Team win %", detail: "z-score" },
      { name: "Team record rank", detail: "among that season's candidates" },
      { name: "Top-2 record", detail: "1 if the team's record ranks first or second" },
      { name: "Won MVP last season", detail: "1 for the defending MVP" },
    ],
  },
  {
    era: 2,
    label: "2008-09 onward",
    seasons: 18,
    summary: "Efficiency and impact: how well, not just how much.",
    features: [
      { name: "True shooting %", detail: "z-score" },
      { name: "Offensive load", detail: "usage % + assist %, z-score" },
      { name: "PIE", detail: "Player Impact Estimate, z-score" },
      { name: "On/off proxy", detail: "player net rating − team margin per game, z-score" },
      { name: "Defensive rating", detail: "inverted so lower is better, z-score" },
      { name: "Games played", detail: "z-score" },
      { name: "Team record rank", detail: "among that season's candidates" },
      { name: "Top-2 record", detail: "1 if the team's record ranks first or second" },
    ],
  },
];

export const MODEL_SETTINGS: { name: string; value: string; why: string }[] = [
  { name: "Algorithm", value: "XGBoost classifier", why: "Gradient-boosted trees handle thresholds such as “top-2 record” without manual interaction terms." },
  {
    name: "Trees",
    value: "100",
    why: "The training sets are tiny: about 194 candidates for a 2008-09-onward season and about 70 before that.",
  },
  { name: "Max depth", value: "3", why: "Shallow trees: each one combines at most three features." },
  { name: "Learning rate", value: "0.1", why: "A standard default; the trees are small, so training is quick anyway." },
  { name: "MVP weight", value: "50×", why: "Only 1 in 11 candidates wins. Weighting MVP examples stops the model from simply predicting “not MVP”." },
];
