export function PageHeader({
  eyebrow,
  title,
  lede,
  actions,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  lede?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-12 grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
      <div className="max-w-3xl">
        {eyebrow && <p className="eyebrow mb-3 text-brand">{eyebrow}</p>}
        <h1 className="font-display text-5xl leading-[0.92] font-bold tracking-tight uppercase sm:text-7xl">{title}</h1>
        {lede && <p className="mt-5 max-w-2xl font-serif text-lg leading-relaxed text-muted-foreground">{lede}</p>}
      </div>
      {actions}
    </header>
  );
}
