import { CheckIcon, XIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ordinal } from "@/lib/format";
import { cn } from "@/lib/utils";

/** "Correct", or how far down the model's list the real MVP was. */
export function VerdictBadge({ correct, actualRank, className }: { correct: boolean; actualRank: number; className?: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(correct ? "border-hit/40 text-hit" : "border-miss/40 text-miss", className)}
    >
      {correct ? <CheckIcon data-icon="inline-start" /> : <XIcon data-icon="inline-start" />}
      {correct ? "Correct" : `MVP ranked ${ordinal(actualRank)}`}
    </Badge>
  );
}
