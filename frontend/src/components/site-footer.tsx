export function SiteFooter() {
  return (
    <footer className="border-t-2 border-foreground/80">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-sm text-muted-foreground sm:grid-cols-[1fr_auto] sm:px-6">
        <div>
          <p className="font-display text-lg font-bold tracking-wide text-foreground uppercase">NBA Analytics</p>
          <p className="mt-1 max-w-xl">
            Regular-season data from NBA.com stats, 2000-01 to the current season. Built as an independent project; not
            affiliated with or endorsed by the NBA.
          </p>
        </div>
        <a
          href="https://github.com/tsetan13821/NBAAnalyticsProject"
          className="eyebrow self-end underline-offset-4 hover:text-foreground hover:underline"
        >
          Source code ↗
        </a>
      </div>
    </footer>
  );
}
