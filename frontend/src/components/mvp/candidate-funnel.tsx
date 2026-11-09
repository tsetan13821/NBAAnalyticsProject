import type { FunnelStep } from "@/content/mvp-method";
import { cn } from "@/lib/utils";

const NUMBER = new Intl.NumberFormat("en-US");

/**
 * Each filter as a row: how many player-seasons survive it, with a bar on a log scale.
 * Log scale because the counts fall from ~10,000 to ~300, and a linear bar would make the
 * last steps invisible.
 */
export function CandidateFunnel({ steps }: { steps: FunnelStep[] }) {
  const max = Math.log10(steps[0].count);
  return (
    <ol className="border-t-2 border-foreground">
      {steps.map((step, index) => {
        const last = index === steps.length - 1;
        const width = (Math.log10(step.count) / max) * 100;
        return (
          <li key={step.rule} className="grid gap-x-6 gap-y-2 border-b py-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
            <div>
              <div className="flex items-baseline gap-3">
                <span className="eyebrow w-5 shrink-0 text-muted-foreground">{index === 0 ? "—" : index}</span>
                <span className="font-display text-xl leading-tight font-bold tracking-tight uppercase">{step.rule}</span>
              </div>
              <p className="mt-1 pl-8 text-sm leading-relaxed text-muted-foreground">{step.why}</p>
            </div>
            <div className="flex items-center gap-3 pl-8 md:pl-0">
              <div className="h-7 flex-1 bg-muted/60">
                <div className={cn("h-full", last ? "bg-brand" : "bg-foreground/70")} style={{ width: `${width}%` }} />
              </div>
              <span className={cn("tabular w-16 text-right font-display text-2xl font-bold", last && "text-brand")}>
                {NUMBER.format(step.count)}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
