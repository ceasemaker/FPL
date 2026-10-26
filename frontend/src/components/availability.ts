// FPL's availability flags and set-piece duties, read the same way on every
// player list: a chip in words ("75%", "Out", "Suspended"), the news split into
// what and when, and short labels for the set pieces a player takes.
import "./availability.css";

export type Tone = "out" | "ban" | "doubt" | "likely" | "gone";
export interface Flag { text: string; tone: Tone }

export function availability(status: string | null | undefined, chance: number | null | undefined): Flag | null {
  if (!status || status === "a") return null;
  if (status === "s") return { text: "Suspended", tone: "ban" };
  if (status === "i" || chance === 0) return { text: "Out", tone: "out" };
  if (status === "d") return { text: chance != null ? `${chance}%` : "Doubt", tone: chance != null && chance >= 75 ? "likely" : "doubt" };
  if (status === "n") return { text: "Not in squad", tone: "gone" };
  return { text: "Unavailable", tone: "gone" };  // "u": mostly left the club or on loan
}

// FPL news reads "Hamstring injury - Expected back 01 Nov": split the what from the when.
export function splitNews(news: string | null | undefined): { injury: string; detail: string } {
  const [head, ...rest] = (news ?? "").split(" - ");
  const detail = rest.join(" - ").trim();
  // "75% chance of playing" repeats the chip; keep only real return news.
  return { injury: head.trim(), detail: /chance of playing/i.test(detail) ? "" : detail };
}

// The availability filter on the Players list (also the ?status= in its address).
export type AvailabilityFilter = "all" | "fit" | "flagged" | "out" | "doubt" | "ban";
export const AVAILABILITY_FILTERS: [AvailabilityFilter, string][] = [
  ["all", "Everyone"], ["fit", "Available"], ["flagged", "Injured, doubtful or banned"], ["out", "Out"], ["doubt", "Doubtful"], ["ban", "Suspended"],
];

export function matchesAvailability(f: AvailabilityFilter, status: string | null | undefined, chance: number | null | undefined): boolean {
  if (f === "all") return true;
  const flag = availability(status, chance);
  if (f === "fit") return !flag;
  if (!flag || flag.tone === "gone") return false;  // departures aren't team news
  if (f === "flagged") return true;
  if (f === "out") return flag.tone === "out";
  if (f === "doubt") return flag.tone === "doubt" || flag.tone === "likely";
  return flag.tone === "ban";
}

export const SET_PIECE_LABEL: Record<string, string> = { penalties: "Pens", corners: "Corners", freeKicks: "Free kicks" };
