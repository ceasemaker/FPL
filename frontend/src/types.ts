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

// ============================================================================
// Top 100 Types
// ============================================================================

export interface Top100Player {
  athlete_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_name: string | null;
  team_short_name: string | null;
  position: string;
  element_type: number;
  now_cost: number;
  total_points: number;
  form: number;
  ownership_count: number;
  ownership_percentage: number;
  image_url: string | null;
  is_starting: boolean;
}

export interface CaptainPick {
  athlete_id: number;
  web_name: string;
  team_short_name: string | null;
  count: number;
  percentage: number;
  image_url: string | null;
}

export interface Top100TemplateData {
  game_week: number;
  manager_count: number;
  average_points: number;
  highest_points: number;
  lowest_points: number;
  template_squad: Top100Player[];
  most_captained: CaptainPick[];
  chip_usage: Record<string, number>;
}

export interface ValuePlayer {
  athlete_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_short_name: string | null;
  now_cost: number;
  now_cost_display: string;
  value_score: number;
  points_last_3: number;
  minutes_last_3: number;
  form: number;
  total_points: number;
  image_url: string | null;
  status: string;
}

export interface BestValueData {
  current_gameweek: number;
  goalkeepers: ValuePlayer[];
  defenders: ValuePlayer[];
  midfielders: ValuePlayer[];
  forwards: ValuePlayer[];
}

export interface ChartDataPoint {
  game_week: number;
  template_points: number;
  average_points: number;
  highest_points: number | null;
  lowest_points: number | null;
  user_points: number | null;
}

export interface UserInfo {
  entry_id: number;
  entry_name: string | null;
  player_name: string | null;
  total_points: number | null;
  overall_rank: number | null;
}

export interface Top100ChartData {
  chart_data: ChartDataPoint[];
  user_info: UserInfo | null;
}

export interface TransferTrend {
  athlete_id: number;
  web_name: string;
  team_short_name: string | null;
  count: number;
  now_cost: number;
  now_cost_display: string;
  total_points: number;
  image_url: string | null;
}

export interface Top100TransfersData {
  game_week: number;
  transfers_in: TransferTrend[];
  transfers_out: TransferTrend[];
}

export interface DifferentialPlayer {
  athlete_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_short_name: string | null;
  position: string;
  ownership_percentage: number;
  ownership_count: number;
  total_points: number;
  now_cost: number;
  now_cost_display: string;
  form: number;
  image_url: string | null;
}

export interface Top100DifferentialsData {
  game_week: number;
  max_ownership: number;
  differentials: DifferentialPlayer[];
}
