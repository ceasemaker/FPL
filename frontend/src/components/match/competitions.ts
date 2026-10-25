// Competitions a Premier League club plays in: short tags and groups, keyed by
// Opta competition id (names vary between feeds, ids don't).

export const COMPETITIONS: Record<number, { tag: string; name: string; group: "league" | "europe" | "cup" }> = {
  8: { tag: "PL", name: "Premier League", group: "league" },
  5: { tag: "UCL", name: "Champions League", group: "europe" },
  6: { tag: "UEL", name: "Europa League", group: "europe" },
  1125: { tag: "UECL", name: "Conference League", group: "europe" },
  174: { tag: "USC", name: "UEFA Super Cup", group: "europe" },
  2: { tag: "EFL", name: "League Cup", group: "cup" },
  1: { tag: "FAC", name: "FA Cup", group: "cup" },
  38: { tag: "CS", name: "Community Shield", group: "cup" },
};

const BY_NAME: Record<string, string> = {
  "Premier League": "PL", "League Cup": "EFL", "English League Cup": "EFL", "FA Cup": "FAC", "English FA Cup": "FAC",
  "UEFA Champions League": "UCL", "Champions League": "UCL", "UEFA Europa League": "UEL", "Europa League": "UEL",
  "UEFA Conference League": "UECL", "Conference League": "UECL", "English Community Shield": "CS", "UEFA Super Cup": "USC",
};

export const compTag = (name: string) => BY_NAME[name] ?? name.split(" ").map((w) => w[0]).join("").slice(0, 4).toUpperCase();
export const compById = (id: number, name = "") => COMPETITIONS[id] ?? { tag: compTag(name), name, group: "cup" as const };
