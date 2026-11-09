export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:justify-between">
        <p>Data from NBA.com stats, 2000-01 to 2025-26. Unofficial project, not affiliated with the NBA.</p>
        <a
          href="https://github.com/tsetan13821/NBAAnalyticsProject"
          className="underline-offset-4 hover:text-foreground hover:underline"
        >
          Source on GitHub
        </a>
      </div>
    </footer>
  );
}
