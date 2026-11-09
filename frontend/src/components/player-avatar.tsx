"use client";

import Image from "next/image";
import { useState } from "react";

import type { PlayerRef } from "@/lib/api/client";
import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";

const SIZES = { sm: 32, md: 40, lg: 64 } as const;

/** NBA.com headshot, falling back to initials when the CDN has no photo (common for early-2000s players). */
export function PlayerAvatar({
  player,
  size = "md",
  className,
}: {
  player: Pick<PlayerRef, "name" | "headshot_url">;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const px = SIZES[size];
  return (
    <span
      className={cn("relative inline-flex shrink-0 items-end justify-center overflow-hidden rounded-full bg-muted", className)}
      style={{ width: px, height: px }}
    >
      {failed ? (
        <span className="self-center text-xs font-medium text-muted-foreground" aria-hidden="true">
          {initials(player.name)}
        </span>
      ) : (
        <Image
          src={player.headshot_url}
          alt=""
          width={Math.round(px * 1.37)}
          height={px}
          className="h-full w-auto max-w-none object-cover"
          onError={() => setFailed(true)}
        />
      )}
    </span>
  );
}
