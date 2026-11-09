"use client";

import { PlusIcon, SearchIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { PlayerAvatar } from "@/components/player-avatar";
import type { PlayerRef } from "@/lib/api/client";
import { type CompareState, compareHref } from "@/lib/compare";

const TYPING_DELAY_MS = 300;

/**
 * The "add a player" search: a plain GET form that keeps the current lineup in hidden fields, so it
 * works before JavaScript loads. Once it has, matches update as you type.
 */
export function AddPlayerForm({ state }: { state: CompareState }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  // Uncontrolled, like the player search: when the URL changes some other way (a player was added,
  // Back), copy it into the field unless it's being typed in.
  const q = state.q ?? "";
  useEffect(() => {
    const input = inputRef.current;
    if (input && input !== document.activeElement) input.value = q;
  }, [q]);

  function go(value: string, history: "push" | "replace") {
    clearTimeout(timer.current);
    router[history](compareHref({ ...state, q: value.trim() || undefined }), { scroll: false });
  }

  return (
    <form
      action="/compare"
      method="get"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        go(inputRef.current?.value ?? "", "push");
      }}
    >
      {state.ids.length > 0 && <input type="hidden" name="ids" value={state.ids.join(",")} />}
      {state.season && <input type="hidden" name="season" value={state.season} />}
      {state.peers === "POSITION" && <input type="hidden" name="peers" value="position" />}
      <label className="relative block">
        <span className="sr-only">Add a player by name</span>
        <SearchIcon
          className="pointer-events-none absolute top-1/2 left-0 size-5 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          ref={inputRef}
          type="search"
          name="q"
          defaultValue={state.q}
          maxLength={50}
          autoComplete="off"
          spellCheck={false}
          placeholder="Add a player…"
          className="w-full border-b-2 border-foreground bg-transparent py-2.5 pl-8 font-display text-2xl font-semibold tracking-tight outline-none placeholder:text-muted-foreground/60 focus-visible:border-brand"
          onChange={(event) => {
            const value = event.currentTarget.value;
            clearTimeout(timer.current);
            timer.current = setTimeout(() => go(value, "replace"), TYPING_DELAY_MS);
          }}
        />
      </label>
    </form>
  );
}

export type Candidate = { player: PlayerRef; detail: string; href: string };

/** Players that can be added, each a link that puts them in the lineup. */
export function CandidateList({ title, candidates }: { title?: string; candidates: Candidate[] }) {
  return (
    <div className="mt-3">
      {title && <p className="eyebrow mb-1 text-muted-foreground">{title}</p>}
      <ul className="grid gap-x-6 sm:grid-cols-2">
        {candidates.map(({ player, detail, href }) => (
          <li key={player.id} className="group relative flex items-center gap-3 border-b py-2 hover:bg-muted/40">
            <PlayerAvatar player={player} size="sm" />
            <span className="min-w-0 flex-1">
              <Link
                href={href}
                scroll={false}
                aria-label={`Add ${player.name}`}
                className="block truncate font-medium after:absolute after:inset-0 group-hover:text-brand"
              >
                {player.name}
              </Link>
              <span className="tabular block truncate text-xs text-muted-foreground">{detail}</span>
            </span>
            <PlusIcon className="size-4 shrink-0 text-muted-foreground group-hover:text-brand" aria-hidden="true" />
          </li>
        ))}
      </ul>
    </div>
  );
}
