"use client";

import Image from "next/image";
import { useState } from "react";

import type { PlayerRef } from "@/lib/api/client";
import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * A large headshot standing on a band of the team's colour, like a trading card. NBA.com headshots
 * are 1040×760 with a transparent background; players without one get their initials instead.
 */
export function PlayerPhoto({
  player,
  color,
  className,
}: {
  player: Pick<PlayerRef, "name" | "headshot_url">;
  color: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={cn("relative aspect-[1040/760] w-full max-w-sm overflow-hidden bg-paper", className)}>
      <div className="absolute inset-x-0 bottom-0 h-2/5 opacity-90" style={{ backgroundColor: color }} aria-hidden="true" />
      {failed ? (
        <span
          className="absolute inset-0 flex items-center justify-center font-display text-8xl font-bold text-muted-foreground/50"
          aria-hidden="true"
        >
          {initials(player.name)}
        </span>
      ) : (
        <Image
          src={player.headshot_url}
          alt={`${player.name} headshot`}
          fill
          loading="eager"
          fetchPriority="high"
          sizes="(min-width: 768px) 352px, 100vw"
          className="object-contain object-bottom"
          onError={() => setFailed(true)}
        />
      )}
    </div>
  );
}
