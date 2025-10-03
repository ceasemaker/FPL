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

    const url = search ? `${API_URL}?search=${encodeURIComponent(search)}` : API_URL;

    fetch(url, {
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
