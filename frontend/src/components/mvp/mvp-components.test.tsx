import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildRaceOption } from "@/components/charts/mvp-race-chart";
import { CANDIDATE_FUNNEL } from "@/content/mvp-method";
import type { EraAccuracy } from "@/lib/api/client";
import { candidate, player, seasonResult } from "@/test/fixtures";

import { CandidateFunnel } from "./candidate-funnel";
import { CandidatesTable } from "./candidates-table";
import { SeasonLedger } from "./season-ledger";
import { describeResult, SeasonStrip } from "./season-strip";
import { ValidationDiagram } from "./validation-diagram";

const hit = seasonResult();
const miss = seasonResult({
  season: "2000-01",
  era: 1,
  predicted: player(406, "Shaquille O'Neal"),
  actual: player(947, "Allen Iverson"),
  actual_rank: 4,
  correct: false,
});
const eras: EraAccuracy[] = [
  { era: 1, label: "2000-01 to 2007-08", correct: 0, seasons: 1 },
  { era: 2, label: "2008-09 onward", correct: 1, seasons: 1 },
];

describe("describeResult", () => {
  it("names the winner on a hit", () => {
    expect(describeResult(hit)).toBe("2024-25: the model picked Shai Gilgeous-Alexander, who won.");
  });

  it("names the pick, the winner and the winner's rank on a miss", () => {
    expect(describeResult(miss)).toBe(
      "2000-01: the model picked Shaquille O'Neal; Allen Iverson won and was the model's 4th choice.",
    );
  });
});

describe("SeasonStrip", () => {
  it("links every season and marks the current one", () => {
    render(<SeasonStrip results={[miss, hit]} current="2024-25" />);
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/mvp/2000-01", "/mvp/2024-25"]);
    expect(links[1]).toHaveAttribute("aria-current", "page");
    expect(links[0]).not.toHaveAttribute("aria-current");
  });

  it("shows a tick for a hit and the MVP's rank for a miss", () => {
    render(<SeasonStrip results={[miss, hit]} />);
    expect(screen.getByRole("link", { name: describeResult(miss) })).toHaveTextContent("4");
    expect(screen.getByRole("link", { name: describeResult(hit) })).toHaveTextContent("✓");
  });
});

describe("SeasonLedger", () => {
  it("groups seasons by era, newest era first", () => {
    render(<SeasonLedger results={[miss, hit]} eras={eras} />);
    const [, modern, early] = screen.getAllByRole("rowgroup"); // the first is the header
    expect(within(modern).getByText("2008-09 onward")).toBeInTheDocument();
    expect(within(modern).getByRole("link", { name: "2024-25" })).toBeInTheDocument();
    expect(within(early).getByRole("link", { name: "2000-01" })).toBeInTheDocument();
  });

  it("shows 'Same' on a hit and both players on a miss", () => {
    render(<SeasonLedger results={[miss, hit]} eras={eras} />);
    const hitRow = screen.getByRole("link", { name: "2024-25" }).closest("tr")!;
    expect(within(hitRow).getByText("Same")).toBeInTheDocument();
    expect(within(hitRow).getByText("Hit")).toBeInTheDocument();

    const missRow = screen.getByRole("link", { name: "2000-01" }).closest("tr")!;
    expect(within(missRow).getByText("Shaquille O'Neal")).toBeInTheDocument();
    expect(within(missRow).getByText("Allen Iverson")).toBeInTheDocument();
    expect(within(missRow).getByText("Miss · MVP 4th")).toBeInTheDocument();
  });
});

describe("CandidateFunnel", () => {
  it("shows every step with its count", () => {
    render(<CandidateFunnel steps={CANDIDATE_FUNNEL} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(CANDIDATE_FUNNEL.length);
    expect(items[0]).toHaveTextContent("10,617");
    expect(items.at(-1)).toHaveTextContent("285");
  });

  it("only keeps fewer players at each step", () => {
    const counts = CANDIDATE_FUNNEL.map((step) => step.count);
    expect(counts).toEqual(counts.toSorted((a, b) => b - a));
  });
});

describe("ValidationDiagram", () => {
  it("draws one row per example season", () => {
    render(<ValidationDiagram examples={["2003-04", "2015-16"]} />);
    expect(screen.getAllByRole("img")).toHaveLength(2);
    expect(screen.getByRole("img", { name: /predict 2015-16/i })).toBeInTheDocument();
  });

  it("ignores seasons outside the data", () => {
    render(<ValidationDiagram examples={["1990-91"]} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
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
