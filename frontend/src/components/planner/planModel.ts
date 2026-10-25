// Transfer planner model: pure functions over the imported squad and a plan
// (a list of transfers by gameweek). Prices are in tenths of £m, like FPL's.

export interface PlannerPlayer {
  id: number; code: number; name: string; fullName: string; team: string; teamShort: string;
  position: "GKP" | "DEF" | "MID" | "FWD" | ""; price: number; points: number; form: number; ppg: number;
  ownership: number; minutes: number; status: string; news: string; chance: number | null; epNext: number | null;
}
export interface SquadPick { id: number; slot: number; purchase: number; selling: number; captain: boolean; vice: boolean }
export interface FixtureCell { opp: string; oppCode: string; home: boolean; difficulty: number | null }
export interface BeforeGame { competition: string; kickoff: string; home: boolean; opp: string }
export interface PlannerData {
  managerId: number; name: string; teamName: string; overallRank: number | null; points: number | null;
  currentGameweek: number; nextGameweek: number; bank: number; teamValue: number | null; freeTransfers: number;
  chips: { key: string; name: string; available: boolean }[];
  squad: SquadPick[];
  gameweeks: { gameweek: number; deadline: string | null }[];
  fixtures: Record<string, Record<string, { fixtures: FixtureCell[]; before: BeforeGame[] }>>;
  players: PlannerPlayer[];
}

export interface Transfer { gw: number; out: number; in: number; sell: number; buy: number }
export interface Plan { name: string; transfers: Transfer[]; bank?: number; freeTransfers?: number }

export const SQUAD_SHAPE: Record<string, number> = { GKP: 2, DEF: 5, MID: 5, FWD: 3 };
export const MAX_PER_CLUB = 3;
export const MAX_FREE = 5;
export const HIT = 4;

export interface Holding { id: number; purchase: number; selling: number }

/** The squad going into gameweek ``gw`` after every planned transfer up to and including it. */
export function squadAt(data: PlannerData, plan: Plan, gw: number): Holding[] {
  let squad: Holding[] = data.squad.map((p) => ({ id: p.id, purchase: p.purchase, selling: p.selling }));
  for (const t of plan.transfers.filter((t) => t.gw <= gw)) {
    squad = squad.map((h) => (h.id === t.out ? { id: t.in, purchase: t.buy, selling: t.buy } : h));
  }
  return squad;
}

export interface WeekSummary {
  gw: number; transfers: Transfer[]; free: number; hits: number; cost: number; bankAfter: number;
  clubsOver: string[]; overBudget: boolean;
}

/** Bank, free transfers and hits for each planned gameweek, in order. */
export function summarise(data: PlannerData, plan: Plan, byId: Map<number, PlannerPlayer>): WeekSummary[] {
  let bank = plan.bank ?? data.bank;
  let free = plan.freeTransfers ?? data.freeTransfers;
  return data.gameweeks.map(({ gameweek: gw }) => {
    const transfers = plan.transfers.filter((t) => t.gw === gw);
    for (const t of transfers) bank += t.sell - t.buy;
    const hits = Math.max(0, transfers.length - free);
    const clubs = new Map<string, number>();
    for (const h of squadAt(data, plan, gw)) {
      const team = byId.get(h.id)?.teamShort ?? "";
      clubs.set(team, (clubs.get(team) ?? 0) + 1);
    }
    const week: WeekSummary = {
      gw, transfers, free, hits, cost: hits * HIT, bankAfter: bank,
      clubsOver: [...clubs].filter(([, n]) => n > MAX_PER_CLUB).map(([c]) => c), overBudget: bank < 0,
    };
    free = Math.min(MAX_FREE, Math.max(0, free - transfers.length) + 1);
    return week;
  });
}

export const money = (tenths: number) => `£${(tenths / 10).toFixed(1)}m`;
