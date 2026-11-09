import type { Metadata } from "next";
import { Barlow, Barlow_Condensed, Source_Serif_4 } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import { THEME_SCRIPT } from "@/lib/theme";

import "./globals.css";

// Barlow for interface text, Barlow Condensed for headlines and numbers (scoreboard feel),
// Source Serif for long-form writing.
const barlow = Barlow({ variable: "--font-barlow", subsets: ["latin"], weight: ["400", "500", "600"] });
const barlowCondensed = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});
const sourceSerif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], style: ["normal", "italic"] });

export const metadata: Metadata = {
  title: { default: "NBA Analytics", template: "%s · NBA Analytics" },
  description:
    "26 seasons of NBA data with machine-learning models: an MVP predictor, player archetypes and a game win-probability model.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // The theme script sets the class before paint, so the server and client markup may differ here.
    <html
      lang="en"
      className={`${barlow.variable} ${barlowCondensed.variable} ${sourceSerif.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <TooltipProvider>
          <SiteHeader />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 pt-10 pb-20 sm:px-6 sm:pt-14">{children}</main>
          <SiteFooter />
        </TooltipProvider>
      </body>
    </html>
  );
}
