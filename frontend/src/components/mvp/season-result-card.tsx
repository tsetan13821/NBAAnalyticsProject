import Link from "next/link";

import { VerdictBadge } from "@/components/mvp/verdict-badge";
import { PlayerAvatar } from "@/components/player-avatar";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MvpSeasonResult, PlayerRef } from "@/lib/api/client";

function PlayerLine({ role, player }: { role: string; player: PlayerRef }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <PlayerAvatar player={player} size="sm" />
      <div className="min-w-0">
        <div className="text-[11px] tracking-wide text-muted-foreground uppercase">{role}</div>
        <div className="truncate text-sm font-medium">{player.name}</div>
      </div>
    </div>
  );
}

export function SeasonResultCard({ result }: { result: MvpSeasonResult }) {
  return (
    <Link
      href={`/mvp/${result.season}`}
      className="group rounded-xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
    >
      <Card size="sm" className="h-full transition-colors group-hover:bg-accent/60">
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="tabular font-semibold">{result.season}</span>
            <VerdictBadge correct={result.correct} actualRank={result.actual_rank} />
          </div>
          {result.correct ? (
            <PlayerLine role="Predicted & won" player={result.actual} />
          ) : (
            <div className="flex flex-col gap-2">
              <PlayerLine role="Model pick" player={result.predicted} />
              <PlayerLine role="Actual MVP" player={result.actual} />
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

export function SeasonResultCardSkeleton() {
  return (
    <Card size="sm">
      <CardContent className="flex flex-col gap-3">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <div className="flex items-center gap-2.5">
          <Skeleton className="size-8 rounded-full" />
          <Skeleton className="h-4 w-32" />
        </div>
      </CardContent>
    </Card>
  );
}
