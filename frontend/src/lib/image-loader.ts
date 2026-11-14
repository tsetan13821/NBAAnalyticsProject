/**
 * next/image loader for player headshots. NBA.com's CDN publishes each headshot in two sizes, so the
 * browser fetches the smallest one that covers the width it needs straight from the CDN: no image
 * optimizer between them (whose free quota a host meters, and whose server the CDN might refuse).
 */
const LARGE = "1040x760";
const SMALL = "260x190";
const SMALL_WIDTH = 260;

export default function headshotLoader({ src, width }: { src: string; width: number }): string {
  if (width <= SMALL_WIDTH && src.includes(`/${LARGE}/`)) return src.replace(`/${LARGE}/`, `/${SMALL}/`);
  return src;
}
