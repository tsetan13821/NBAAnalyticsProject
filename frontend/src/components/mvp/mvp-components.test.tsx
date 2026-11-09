import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildRaceOption } from "@/components/charts/mvp-race-chart";
import { candidate, player, seasonResult } from "@/test/fixtures";

import { CandidatesTable } from "./candidates-table";
import { SeasonResultCard } from "./season-result-card";
import { VerdictBadge } from "./verdict-badge";

describe("VerdictBadge", () => {
  it("shows a correct pick", () => {
    render(<VerdictBadge correct actualRank={1} />);
    expect(screen.getByText("Correct")).toBeInTheDocument();
  });

  it("shows where the real MVP ranked on a miss", () => {
    render(<VerdictBadge correct={false} actualRank={3} />);
    expect(screen.getByText("MVP ranked 3rd")).toBeInTheDocument();
  });
});

describe("SeasonResultCard", () => {
  it("links to the season and shows one player when the pick was right", () => {
    render(<SeasonResultCard result={seasonResult()} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/mvp/2024-25");
    expect(screen.getByText("Predicted & won")).toBeInTheDocument();
    expect(screen.getAllByText("Shai Gilgeous-Alexander")).toHaveLength(1);
  });

  it("shows the pick and the winner on a miss", () => {
    const result = seasonResult({
      season: "2000-01",
      era: 1,
      predicted: player(406, "Shaquille O'Neal"),
      actual: player(947, "Allen Iverson"),
      actual_rank: 2,
      correct: false,
    });
    render(<SeasonResultCard result={result} />);
    expect(screen.getByText("Model pick").nextSibling).toHaveTextContent("Shaquille O'Neal");
    expect(screen.getByText("Actual MVP").nextSibling).toHaveTextContent("Allen Iverson");
    expect(screen.getByText("MVP ranked 2nd")).toBeInTheDocument();
  });
});

describe("CandidatesTable", () => {
  it("lists candidates in rank order and marks the MVP", () => {
    const candidates = [candidate(1, "Player One"), candidate(2, "Player Two", { is_mvp: true })];
    render(<CandidatesTable candidates={candidates} />);

    const rows = screen.getAllByRole("row").slice(1); // skip the header
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("Player One")).toBeInTheDocument();
    expect(within(rows[0]).queryByText("MVP")).not.toBeInTheDocument();
    expect(within(rows[1]).getByText("MVP")).toBeInTheDocument();
    expect(within(rows[1]).getByText("25.0%")).toBeInTheDocument(); // score share 0.25
  });
});

describe("buildRaceOption", () => {
  const palette = { brand: "orange", muted: "grey", text: "white", subtle: "silver", grid: "black", popover: "navy" };

  it("highlights only the real MVP and keeps rank order", () => {
    const candidates = [candidate(1, "LeBron James"), candidate(2, "Kevin Durant", { is_mvp: true })];
    const option = buildRaceOption(candidates, palette) as {
      yAxis: { data: string[] };
      series: { data: { value: number; itemStyle: { color: string } }[] }[];
    };
    expect(option.yAxis.data).toEqual(["L. James", "K. Durant"]);
    expect(option.series[0].data.map((d) => d.itemStyle.color)).toEqual(["grey", "orange"]);
    expect(option.series[0].data.map((d) => d.value)).toEqual([0.5, 0.25]);
  });
});
