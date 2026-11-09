import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
      <p className="tabular text-5xl font-semibold text-brand">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground">That page or season isn&apos;t in the dataset.</p>
      <Link href="/" className={buttonVariants()}>
        Back to overview
      </Link>
    </div>
  );
}
