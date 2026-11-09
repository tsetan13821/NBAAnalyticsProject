"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function Error({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Couldn&apos;t load this page</h1>
      <p className="text-muted-foreground">
        The data service didn&apos;t respond. If you&apos;re running locally, check that the API is up on port 8000.
      </p>
      <Button onClick={() => retry()}>Try again</Button>
    </div>
  );
}
