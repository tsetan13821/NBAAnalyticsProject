"use client";

import { SearchIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { hasFilters, type PlayerFilters, parsePlayerFilters, playersHref, POSITIONS } from "@/lib/player-search";
import { cn } from "@/lib/utils";

const TYPING_DELAY_MS = 300;

/** Read the form into filters, always back on page 1. */
function readForm(form: HTMLFormElement): PlayerFilters {
  const data = Object.fromEntries(new FormData(form)) as Record<string, string>;
  return { ...parsePlayerFilters(data), page: 1 };
}

/**
 * A plain GET form, so it works before JavaScript loads. Once it has, results update as you type
 * (after a short pause) and as soon as a filter changes, and the URL keeps the search shareable.
 */
export function PlayerSearchForm({
  filters,
  teams,
  seasons,
  currentSeason,
}: {
  filters: PlayerFilters;
  teams: { abbr: string; name: string }[];
  /** Newest first */
  seasons: string[];
  /** The season under way, labelled as such in the list. */
  currentSeason?: string;
}) {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  // The fields are uncontrolled (so typing never waits on a render). When the URL changes some other
  // way (back/forward, "Clear all"), copy it into every field except the one being typed in.
  const { q = "", position = "", team = "", season = "" } = filters;
  useEffect(() => {
    const form = formRef.current;
    if (!form) return;
    const values: Record<string, string> = { q, pos: position, team, season };
    for (const [name, value] of Object.entries(values)) {
      const field = form.elements.namedItem(name) as HTMLInputElement | HTMLSelectElement | null;
      if (field && field !== document.activeElement) field.value = value;
    }
  }, [q, position, team, season]);

  /** Typing replaces the history entry instead of adding one per pause; a filter change adds one, so Back undoes it. */
  function go(form: HTMLFormElement, history: "push" | "replace" = "push") {
    clearTimeout(timer.current);
    router[history](playersHref(readForm(form)), { scroll: false });
  }

  return (
    <form
      ref={formRef}
      action="/players"
      method="get"
      role="search"
      className="mb-10"
      onSubmit={(event) => {
        event.preventDefault();
        go(event.currentTarget);
      }}
    >
      <label className="relative block">
        <span className="sr-only">Player name</span>
        <SearchIcon
          className="pointer-events-none absolute top-1/2 left-0 size-6 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          type="search"
          name="q"
          defaultValue={filters.q}
          maxLength={50}
          autoComplete="off"
          spellCheck={false}
          placeholder="Search by name…"
          className="w-full border-b-2 border-foreground bg-transparent py-3 pl-9 font-display text-3xl font-semibold tracking-tight outline-none placeholder:text-muted-foreground/60 focus-visible:border-brand sm:text-4xl"
          onChange={(event) => {
            const form = event.currentTarget.form!;
            clearTimeout(timer.current);
            timer.current = setTimeout(() => go(form, "replace"), TYPING_DELAY_MS);
          }}
        />
      </label>

      <div className="mt-4 flex flex-wrap items-end gap-x-4 gap-y-3">
        <Filter label="Position">
          <select name="pos" defaultValue={filters.position ?? ""} onChange={(e) => go(e.currentTarget.form!)} className={SELECT}>
            <option value="">All positions</option>
            {POSITIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </Filter>
        <Filter label="Played for">
          <select name="team" defaultValue={filters.team ?? ""} onChange={(e) => go(e.currentTarget.form!)} className={SELECT}>
            <option value="">Any team</option>
            {teams.map((t) => (
              <option key={t.abbr} value={t.abbr}>
                {t.name}
              </option>
            ))}
          </select>
        </Filter>
        <Filter label="Season">
          <select name="season" defaultValue={filters.season ?? ""} onChange={(e) => go(e.currentTarget.form!)} className={cn(SELECT, "tabular")}>
            <option value="">Any season</option>
            {seasons.map((s) => (
              <option key={s} value={s}>
                {s === currentSeason ? `${s} (in progress)` : s}
              </option>
            ))}
          </select>
        </Filter>
        <button type="submit" className="eyebrow h-9 bg-foreground px-4 text-background hover:bg-brand hover:text-brand-foreground">
          Search
        </button>
        {hasFilters(filters) && (
          <Link href="/players" scroll={false} className="eyebrow h-9 content-center text-muted-foreground hover:text-foreground">
            Clear all
          </Link>
        )}
      </div>
    </form>
  );
}

const SELECT =
  "h-9 min-w-36 cursor-pointer border border-input bg-background px-2.5 text-sm outline-none hover:border-foreground/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function Filter({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="eyebrow text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}
