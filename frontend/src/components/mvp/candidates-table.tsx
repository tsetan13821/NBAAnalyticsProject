import { TrophyIcon } from "lucide-react";

import { PlayerAvatar } from "@/components/player-avatar";
import { TeamBadge } from "@/components/team-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { MvpCandidate } from "@/lib/api/client";
import { ordinal, percent, stat } from "@/lib/format";
import { cn } from "@/lib/utils";

const NUMERIC = "text-right tabular";

export function CandidatesTable({ candidates }: { candidates: MvpCandidate[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10 text-right">#</TableHead>
          <TableHead>Player</TableHead>
          <TableHead className={NUMERIC}>Model share</TableHead>
          <TableHead className={NUMERIC}>PTS</TableHead>
          <TableHead className={NUMERIC}>REB</TableHead>
          <TableHead className={NUMERIC}>AST</TableHead>
          <TableHead className={NUMERIC}>TS%</TableHead>
          <TableHead className={NUMERIC} title="Player Impact Estimate">PIE</TableHead>
          <TableHead className={NUMERIC}>GP</TableHead>
          <TableHead className={NUMERIC}>Team</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {candidates.map((c) => (
          <TableRow key={c.player.id} className={cn(c.is_mvp && "bg-brand/8 hover:bg-brand/12")}>
            <TableCell className={cn(NUMERIC, "text-muted-foreground")}>{c.rank}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2.5">
                <PlayerAvatar player={c.player} size="sm" />
                <span className="font-medium">{c.player.name}</span>
                {c.is_mvp && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-brand">
                    <TrophyIcon className="size-3.5" aria-hidden="true" />
                    MVP
                  </span>
                )}
              </div>
            </TableCell>
            <TableCell className={cn(NUMERIC, "font-medium")}>{percent(c.score_share)}</TableCell>
            <TableCell className={NUMERIC}>{stat(c.stats.pts_pg)}</TableCell>
            <TableCell className={NUMERIC}>{stat(c.stats.reb_pg)}</TableCell>
            <TableCell className={NUMERIC}>{stat(c.stats.ast_pg)}</TableCell>
            <TableCell className={NUMERIC}>{percent(c.stats.ts_pct)}</TableCell>
            <TableCell className={NUMERIC}>{percent(c.stats.pie)}</TableCell>
            <TableCell className={NUMERIC}>{c.stats.games}</TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-2 text-right">
                <span className="tabular text-xs text-muted-foreground">
                  {percent(c.team_win_pct, 0)} · {ordinal(c.team_conference_rank)}
                </span>
                <TeamBadge team={c.team} />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
