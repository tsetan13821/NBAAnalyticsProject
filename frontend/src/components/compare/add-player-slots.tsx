"use client";

import { Dialog } from "@base-ui/react/dialog";
import { PlusIcon, XIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { type CompareState, compareHref, MAX_PLAYERS } from "@/lib/compare";
import { cn } from "@/lib/utils";

/**
 * The lineup's open slots. Each is a button that opens the player picker: `children`, the search
 * box and its suggestions or matches, rendered on the server and kept up to date as the URL changes.
 *
 * Give this a new `key` when the lineup changes, so adding a player closes the picker.
 */
export function AddPlayerSlots({ state, children }: { state: CompareState; children: React.ReactNode }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);
  const filled = state.ids.length;
  const empty = MAX_PLAYERS - filled;

  // Typing saves the search in the URL by replacing the current history entry. Coming back to that
  // entry later (Back after adding a player) should show the page, not reopen an old search, so a
  // search found in the URL on arrival is cleared.
  const staleSearch = useRef(state.q ? compareHref({ ...state, q: undefined }) : null);
  useEffect(() => {
    if (staleSearch.current) router.replace(staleSearch.current, { scroll: false });
  }, [router]);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        // Dismissed (Esc, the close button, a click outside): drop the half-typed search from the URL.
        if (!next && state.q) router.replace(compareHref({ ...state, q: undefined }), { scroll: false });
      }}
    >
      {Array.from({ length: empty }, (_, i) => (
        <li
          key={i}
          className={cn(
            "md:flex",
            // Phones show only the first open slot, full width when it would otherwise sit alone.
            i === 0 ? "flex" : "hidden",
            i === 0 && filled % 2 === 0 && "max-md:col-span-2",
          )}
        >
          <Dialog.Trigger
            className={cn(
              "group flex w-full flex-col items-center justify-center gap-2 border border-dashed text-muted-foreground transition-colors",
              "hover:border-brand hover:bg-paper hover:text-brand focus-visible:border-brand focus-visible:text-brand focus-visible:outline-none",
              filled === 0 || i === 0 ? "min-h-36" : "min-h-36 max-md:min-h-24",
            )}
          >
            <span className="grid size-11 place-items-center rounded-full border border-current">
              <PlusIcon className="size-5" aria-hidden="true" />
            </span>
            <span className="eyebrow">Add player</span>
          </Dialog.Trigger>
        </li>
      ))}

      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px] transition-opacity duration-150 data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
        <Dialog.Popup
          ref={popupRef}
          initialFocus={() => popupRef.current?.querySelector<HTMLInputElement>("input[type=search]") ?? true}
          // Picking a player is a link to the new lineup: close at once rather than wait for the page.
          onClick={(event) => {
            if ((event.target as HTMLElement).closest("a[href]")) setOpen(false);
          }}
          className={cn(
            "fixed z-50 flex flex-col overflow-hidden border-t-[3px] border-t-brand bg-background shadow-2xl outline-none",
            "transition-[opacity,translate] duration-150 data-[ending-style]:opacity-0 data-[starting-style]:opacity-0",
            // Phones: a sheet from the bottom. Wider screens: a panel near the top, clear of the lineup's height.
            "inset-x-0 bottom-0 max-h-[85dvh] data-[ending-style]:translate-y-4 data-[starting-style]:translate-y-4",
            "md:inset-x-auto md:bottom-auto md:top-[12vh] md:left-1/2 md:max-h-[76vh] md:w-[min(42rem,calc(100vw-2rem))] md:-translate-x-1/2 md:border md:data-[ending-style]:translate-y-0 md:data-[starting-style]:translate-y-0",
          )}
        >
          <div className="flex items-start justify-between gap-4 px-5 pt-4">
            <div>
              <Dialog.Title className="font-display text-2xl font-bold tracking-tight uppercase">Add a player</Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground">
                Player {filled + 1} of up to {MAX_PLAYERS}. Search by name, or pick a suggestion.
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label="Close"
              className="-mr-1.5 grid size-8 shrink-0 place-items-center text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <XIcon className="size-4" />
            </Dialog.Close>
          </div>
          <div className="overflow-y-auto px-5 pt-2 pb-6">{children}</div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
