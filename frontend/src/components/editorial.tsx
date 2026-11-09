/** Layout pieces shared by every page: numbered sections, scoreboard figures, decision notes. */
import { cn } from "@/lib/utils";

/** A heavy rule, a section number and a condensed title, like a newspaper section front. */
export function SectionHeading({
  number,
  title,
  aside,
  id,
  className,
}: {
  number?: string;
  title: React.ReactNode;
  aside?: React.ReactNode;
  id?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-6 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t-2 border-foreground pt-3", className)}>
      {number && <span className="eyebrow text-brand">{number}</span>}
      <h2 id={id} className="scroll-mt-24 font-display text-3xl leading-none font-bold tracking-tight uppercase">
        {title}
      </h2>
      {aside && <div className="ml-auto text-sm text-muted-foreground">{aside}</div>}
    </div>
  );
}

export function Section({ className, ...props }: React.ComponentProps<"section">) {
  return <section className={cn("mt-16 first:mt-0", className)} {...props} />;
}

/** One big scoreboard number. Use inside <FigureRow>. */
export function Figure({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  tone?: "default" | "brand";
}) {
  return (
    <div className="flex flex-col gap-1 py-4 sm:px-6 sm:first:pl-0">
      <dt className="eyebrow order-2 text-muted-foreground">{label}</dt>
      <dd
        className={cn(
          "tabular order-1 font-display text-6xl leading-none font-bold tracking-tight",
          tone === "brand" && "text-brand",
        )}
      >
        {value}
      </dd>
      {detail && <dd className="order-3 text-sm text-muted-foreground">{detail}</dd>}
    </div>
  );
}

/** Figures side by side, separated by hairlines. */
export function FigureRow({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <dl
      className={cn(
        "grid grid-cols-2 divide-border border-y sm:flex sm:divide-x [&>div]:border-border max-sm:[&>div:nth-child(n+3)]:border-t",
        className,
      )}
    >
      {children}
    </dl>
  );
}

/** A design decision and the reasoning behind it. */
export function Decision({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <aside className="my-8 border-l-[3px] border-brand bg-paper py-4 pr-5 pl-5">
      <p className="eyebrow text-brand">Decision</p>
      <p className="mt-1 font-display text-xl leading-tight font-bold tracking-tight uppercase">{title}</p>
      <div className="mt-2 text-[0.95rem] leading-relaxed text-muted-foreground">{children}</div>
    </aside>
  );
}
