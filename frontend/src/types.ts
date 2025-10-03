export interface PlayerMover {
  id: number;
  first_name: string;
  second_name: string;
  team: string | null;
  value: number;
  now_cost: number | null;
  total_points: number | null;
  change_label: string;
  image_url: string | null;
}

export interface PriceMovers {
  risers: PlayerMover[];
  fallers: PlayerMover[];
}

export interface Movers {
  price: PriceMovers;
  points: PlayerMover[];
}

export interface Transfers {
  in: PlayerMover[];
  out: PlayerMover[];
}

export interface FixturePressureEntry {
  team: string;
  score: number;
}

export interface FixturePressureResponse {
  easiest: FixturePressureEntry[];
  hardest: FixturePressureEntry[];
}

export interface PulseResponse {
  value: number;
  total_points_current: number;
  total_transfers_in_event: number;
  snapshot_counts: Record<string, number>;
  last_updated: string | null;
}

export interface NewsItem {
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_code: number | null;
  news: string;
  news_added: string | null;
  image_url: string | null;
}

export interface LandingData {
  current_gameweek: number;
  pulse: PulseResponse;
  movers: Movers;
  transfers: Transfers;
  fixture_pressure: FixturePressureResponse;
  news: NewsItem[];
}
