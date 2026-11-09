import { cn } from "@/lib/utils";

const FIRST_START_YEAR = 2000;
const SEASONS = Array.from({ length: 26 }, (_, i) => {
  const start = FIRST_START_YEAR + i;
  return { season: `${start}-${String(start + 1).slice(2)}`, era: start <= 2007 ? 1 : 2 };
});

type Role = "test" | "train" | "unused";

function roleOf(season: { season: string; era: number }, target: { season: string; era: number }): Role {
  if (season.season === target.season) return "test";
  return season.era === target.era ? "train" : "unused";
}

const ROLE_STYLE: Record<Role, string> = {
  test: "bg-brand",
  train: "bg-foreground/60",
  unused: "bg-[repeating-linear-gradient(135deg,transparent_0_3px,var(--border)_3px_5px)]",
};

/** Leave-one-season-out within an era, drawn for two example seasons. */
export function ValidationDiagram({ examples = ["2003-04", "2015-16"] }: { examples?: string[] }) {
  return (
    <figure className="overflow-x-auto">
      <div className="min-w-[36rem]">
        <div className="grid grid-cols-[6.5rem_1fr] items-end gap-3">
          <span />
          <div className="grid grid-cols-26 gap-px">
            {SEASONS.map((s, i) => (
              <span key={s.season} className="tabular text-center font-display text-[0.65rem] text-muted-foreground">
                {i % 5 === 0 ? `’${s.season.slice(2, 4)}` : ""}
              </span>
            ))}
          </div>
        </div>
        {examples.map((example) => {
          const target = SEASONS.find((s) => s.season === example);
          if (!target) return null;
          return (
            <div key={example} className="mt-1.5 grid grid-cols-[6.5rem_1fr] items-center gap-3">
              <span className="eyebrow text-right text-muted-foreground">Predict {example}</span>
              <div className="grid grid-cols-26 gap-px" role="img" aria-label={`To predict ${example}, train on the other seasons of its era only.`}>
                {SEASONS.map((s) => (
                  <span
                    key={s.season}
                    className={cn("h-7", ROLE_STYLE[roleOf(s, target)], s.season === "2008-09" && "ml-0.5")}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <figcaption className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="size-3 bg-brand" aria-hidden="true" /> Season being predicted
        </span>
        <span className="flex items-center gap-2">
          <span className="size-3 bg-foreground/60" aria-hidden="true" /> Training data
        </span>
        <span className="flex items-center gap-2">
          <span className={cn("size-3 border", ROLE_STYLE.unused)} aria-hidden="true" /> Other era, not used
        </span>
      </figcaption>
    </figure>
  );
}
