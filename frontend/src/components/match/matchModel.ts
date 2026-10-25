// The Match page's data and the "match at minute X" logic (pure, so it can be
// tested). One cursor index drives everything: an index into Opta's momentum
// series, which runs 1..47ish for the first half and 46..94ish for the second.

export interface TeamRef { id: string; name: string; short: string }
export interface Goal { minute: number; period: number; team: string; scorer: string; assist: string | null; type: string; home: number; away: number }
export interface MatchEventRow { minute: number; period: number; team_id: string; kind: string; player_name: string; other_player_name: string; detail: string }
export interface LineupPlayer {
  team_id: string; player_id: string; name: string; shirt: string; position: string; position_side: string;
  formation_place: number | null; formation_row: number | null; formation_col: number | null;
  starter: boolean; captain: boolean; minute_on: number | null; minute_off: number | null;
}
// Cup and European rows carry only minutes, goals and assists (the rest null).
export interface PlayerRow {
  id: string; name: string; team: string; position: string; minutes: number; started: boolean; fpl: number | null;
  goals: number; assists: number; shots: number | null; boxShots: number | null; bigChances: number | null; chances: number | null;
  boxTouches: number | null; passes: number | null; accuratePasses: number | null; defence: number | null; saves: number | null;
}
export interface FormRow { matchId: string; opp: string; home: boolean; gf: number; ga: number; res: "W" | "D" | "L"; date: string | null; competition: string; league: boolean }
export interface MatchData {
  matchId: string; season: number; gameweek: number | null; kickoff: string | null; status: "finished" | "upcoming";
  competition: string; competitionId: number; round: string; penalties: [number, number] | null;
  home: TeamRef; away: TeamRef; score: [number, number] | null;
  goals: Goal[]; events: MatchEventRow[]; momentum: [number, number, number, number][];
  lineups: LineupPlayer[]; teamStats: Record<string, Record<string, number | string | null>>; players: PlayerRow[];
  fplDouble: string[]; detailsAvailable: boolean; playersAvailable: boolean;
  form: { home: FormRow[]; away: FormRow[] };
  h2h: { matchId: string; date: string | null; home: string; away: string; hs: number; as: number; competition: string }[];
  odds: { fixtureId: number; home?: number; draw?: number | null; away?: number | null; chances?: number[] | null; updated?: string | null } | null;
}

export type Kind = "goal" | "yellow" | "second_yellow" | "red" | "sub" | "var";
export interface TimelineEvent { kind: Kind; minute: number; period: number; team: string; player: string; other: string | null; detail: string; home?: number; away?: number; idx: number }
export interface Moment { period: number; minute: number; h: number; a: number }

export interface Timeline {
  moments: Moment[];
  end: number;          // number of moments
  halfIndex: number;    // first moment of the second half
  events: TimelineEvent[];
  label: (i: number) => string;
  indexOf: (minute: number, period?: number) => number;
}

export function buildTimeline(d: MatchData): Timeline {
  let moments: Moment[] = d.momentum.map(([period, minute, h, a]) => ({ period, minute, h, a }));
  if (!moments.length) {
    // No momentum feed (cup and European matches): a plain axis so the
    // timeline still works, with extra time when the match went to it.
    const extra = d.goals.some((g) => g.minute > 90) || d.events.some((e) => e.period >= 3 || e.minute > 95);
    moments = [
      ...Array.from({ length: 45 }, (_, k) => ({ period: 1, minute: k + 1, h: 0, a: 0 })),
      ...Array.from({ length: 45 }, (_, k) => ({ period: 2, minute: k + 46, h: 0, a: 0 })),
      ...(extra ? Array.from({ length: 30 }, (_, k) => ({ period: 3, minute: k + 91, h: 0, a: 0 })) : []),
    ];
  }
  const halfIndex = Math.max(1, moments.findIndex((m) => m.period === 2));
  const indexOf = (minute: number, period?: number) => {
    let p = period ?? (minute > 90 ? 3 : minute > 45 ? 2 : 1);
    if (p >= 3) p = moments.some((m) => m.period === 3) ? 3 : 2;
    const k = moments.findIndex((m) => m.period === p && m.minute >= minute);
    return k < 0 ? (p === 1 ? halfIndex - 1 : moments.length - 1) : k;
  };
  const label = (i: number) => {
    const m = moments[Math.max(0, Math.min(i, moments.length - 1))];
    if (!m) return "0′";
    if (m.period === 1 && m.minute > 45) return `45+${m.minute - 45}′`;
    if (m.period === 2 && m.minute > 90) return `90+${m.minute - 90}′`;
    return `${m.minute}′`;
  };
  const events: TimelineEvent[] = [
    ...d.goals.map((g) => ({ kind: "goal" as Kind, minute: g.minute, period: g.period, team: g.team, player: g.scorer, other: g.assist, detail: g.type, home: g.home, away: g.away, idx: 0 })),
    ...d.events.map((e) => ({ kind: e.kind as Kind, minute: e.minute, period: e.period, team: e.team_id, player: e.player_name, other: e.other_player_name || null, detail: e.detail, idx: 0 })),
  ].map((e) => ({ ...e, idx: indexOf(e.minute, e.period) })).sort((a, b) => a.idx - b.idx);
  return { moments, end: moments.length, halfIndex, events, label, indexOf };
}

// Event names are short ("R. Gravenberch"); lineups carry full names.
const surname = (n: string) => { const p = n.replace(/^[A-Z]\.\s*/, "").split(" "); return p[p.length - 1].toLowerCase(); };
export function findPlayer(lineups: LineupPlayer[], team: string, name: string | null): LineupPlayer | undefined {
  if (!name) return undefined;
  const clean = name.replace(/\s*\(own goal\)$/, "");
  return lineups.find((p) => p.team_id === team && p.name === clean)
    ?? lineups.find((p) => p.team_id === team && surname(p.name) === surname(clean));
}

export interface Slot { row: number; col: number }
export function slots(d: MatchData): Record<string, Slot> {
  const out: Record<string, Slot> = {};
  for (const p of d.lineups) if (p.starter && p.formation_row != null && p.formation_col != null) out[p.player_id] = { row: p.formation_row, col: p.formation_col };
  // A substitute takes the slot of the player he replaced.
  for (const e of d.events.filter((x) => x.kind === "sub")) {
    const on = findPlayer(d.lineups, e.team_id, e.player_name), off = findPlayer(d.lineups, e.team_id, e.other_player_name);
    if (on && off && out[off.player_id]) out[on.player_id] = out[off.player_id];
  }
  return out;
}

export interface OnPitch extends LineupPlayer { sentOff: boolean; fresh: boolean; goals: number; cards: Kind[] }
export interface MinuteState {
  index: number; score: [number, number]; players: OnPitch[]; men: Record<string, number>;
  events: TimelineEvent[]; spell: { home: number; away: number };
}

export function stateAt(d: MatchData, t: Timeline, slotMap: Record<string, Slot>, i: number): MinuteState {
  const seen = t.events.filter((e) => e.idx <= i);
  let score: [number, number] = [0, 0];
  for (const g of seen) if (g.kind === "goal") score = [g.home ?? 0, g.away ?? 0];
  const sentOff = new Set(seen.filter((e) => e.kind === "red" || e.kind === "second_yellow").map((e) => findPlayer(d.lineups, e.team, e.player)?.player_id));
  const at = (minute: number | null) => (minute == null ? Infinity : t.indexOf(minute));
  const players: OnPitch[] = [];
  for (const p of d.lineups) {
    if (!slotMap[p.player_id]) continue;
    const onIdx = p.starter ? -1 : at(p.minute_on);
    const offIdx = at(p.minute_off);
    if (onIdx > i) continue;
    const red = sentOff.has(p.player_id);
    if (offIdx <= i && !red) continue;
    players.push({
      ...p, sentOff: red, fresh: !p.starter && i - onIdx >= 0 && i - onIdx <= 3,
      goals: seen.filter((e) => e.kind === "goal" && e.detail !== "Own" && findPlayer(d.lineups, e.team, e.player)?.player_id === p.player_id).length,
      cards: seen.filter((e) => ["yellow", "second_yellow", "red"].includes(e.kind) && findPlayer(d.lineups, e.team, e.player)?.player_id === p.player_id).map((e) => e.kind),
    });
  }
  const men = {
    [d.home.id]: players.filter((p) => p.team_id === d.home.id && !p.sentOff).length,
    [d.away.id]: players.filter((p) => p.team_id === d.away.id && !p.sentOff).length,
  };
  const window = t.moments.slice(Math.max(0, i - 9), i + 1);
  return {
    index: i, score, players, men, events: seen,
    spell: { home: window.reduce((s, m) => s + m.h, 0), away: window.reduce((s, m) => s + m.a, 0) },
  };
}

// One plain sentence about how the match went, built only from facts in the data.
export function summary(d: MatchData, t: Timeline): string | null {
  if (d.status !== "finished" || !d.score) return null;
  const [hs, as] = d.score;
  const red = t.events.find((e) => e.kind === "second_yellow" || e.kind === "red");
  const winner = hs > as ? d.home : as > hs ? d.away : null;
  if (red && winner && red.team !== winner.id) {
    const after = t.events.filter((e) => e.kind === "goal" && e.team === winner.id && e.idx > red.idx);
    const allAfter = after.length > 0 && after.length === t.events.filter((e) => e.kind === "goal" && e.team === winner.id).length;
    const who = findPlayer(d.lineups, red.team, red.player)?.name ?? red.player;
    if (allAfter && hs + as === after.length) {
      const words = ["", "one", "two", "three", "four", "five", "six", "seven"];
      const goalsText = after.length === 1 ? "the only goal" : after.length === 2 ? "both goals" : `all ${words[after.length] ?? after.length} goals`;
      return `Level until ${who} was sent off ${red.kind === "second_yellow" ? "for a second yellow " : ""}on ${red.minute}′. ${winner.name} scored ${goalsText} in the ${after[after.length - 1].minute - red.minute} minutes that followed.`;
    }
  }
  const goals = t.events.filter((e) => e.kind === "goal");
  if (!goals.length) return `A goalless draw.`;
  const lastLeadChange = goals.reduce<TimelineEvent | null>((acc, g) => ((g.home ?? 0) !== (g.away ?? 0) ? acc ?? g : null), null);
  if (winner && lastLeadChange) {
    return `${winner.name} led from ${lastLeadChange.minute}′ and won ${Math.max(hs, as)}–${Math.min(hs, as)}.`;
  }
  return winner ? `${winner.name} won ${Math.max(hs, as)}–${Math.min(hs, as)}.` : `It finished level at ${hs}–${as}.`;
}
