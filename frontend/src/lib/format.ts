/** Display helpers. The API returns percentages as fractions (0.512 = 51.2%). */

const SEASON_PATTERN = /^\d{4}-\d{2}$/;

export function isSeason(value: string): boolean {
  if (!SEASON_PATTERN.test(value)) return false;
  const start = Number(value.slice(0, 4));
  return (start + 1) % 100 === Number(value.slice(5));
}

/** 0.5123 -> "51.2%" */
export function percent(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** 27.345 -> "27.3" */
export function stat(value: number, digits = 1): string {
  return value.toFixed(digits);
}

/** 19, 26 -> "19/26" */
export function ratio(part: number, whole: number): string {
  return `${part}/${whole}`;
}

/** 1 -> "1st", 2 -> "2nd", 11 -> "11th" */
export function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th"}`;
}

/** "Shai Gilgeous-Alexander" -> "SG" */
export function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts;
  return letters.map((part) => part[0]).join("").toUpperCase();
}

/** "LeBron James" -> "L. James" (for tight chart axes) */
export function shortName(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length < 2) return name;
  return `${parts[0][0]}. ${parts.slice(1).join(" ")}`;
}

/** "2000-01", "2025-26" -> 26 */
export function seasonCount(first: string, last: string): number {
  return Number(last.slice(0, 4)) - Number(first.slice(0, 4)) + 1;
}

/** Neighbouring seasons in a list sorted oldest first. */
export function adjacentSeasons(seasons: string[], current: string): { previous?: string; next?: string } {
  const index = seasons.indexOf(current);
  if (index === -1) return {};
  return { previous: seasons[index - 1], next: seasons[index + 1] };
}
