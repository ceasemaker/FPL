import { useState, useEffect } from "react";

export interface Player {
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_id: number | null;
  team_code: number | null;
  now_cost: number;
  total_points: number;
  form: number | null;
  avg_fdr: number | null;
  element_type: number;
  image_url: string | null;
  status: string | null;
  goals_scored: number;
  assists: number;
  expected_goals: number | null;
  points_last_3: number;
  minutes_last_3: number;
  news: string | null;
}

interface PlayersResponse {
  players: Player[];
  count: number;
}

const API_URL = import.meta.env.VITE_API_PLAYERS_URL ?? "/api/players/";

export function usePlayers(search: string = "") {
  const [data, setData] = useState<PlayersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    // Fetch all players (page_size=1000) to allow client-side filtering
    const url = new URL(API_URL, window.location.origin);
    if (search) url.searchParams.append("search", search);
    url.searchParams.append("page_size", "1000");

    fetch(url.toString(), {
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: PlayersResponse = await response.json();
        if (isMounted) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load players", err);
          setError(err.message ?? "Unexpected error");
          setData(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [search]);

  return {
    data,
    isLoading,
    error,
  };
}
