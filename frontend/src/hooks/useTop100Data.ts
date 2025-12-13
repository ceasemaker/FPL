import { useEffect, useState, useCallback } from "react";
import {
  Top100TemplateData,
  BestValueData,
  Top100ChartData,
  Top100TransfersData,
  Top100DifferentialsData,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

/**
 * Hook to fetch Top 100 template team data
 */
export function useTop100Template(gameweek?: number) {
  const [data, setData] = useState<Top100TemplateData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    const url = gameweek
      ? `${API_BASE}/api/top100/template/?gameweek=${gameweek}`
      : `${API_BASE}/api/top100/template/`;

    fetch(url, { headers: { Accept: "application/json" } })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: Top100TemplateData = await response.json();
        if (isMounted) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load Top 100 template data", err);
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
  }, [gameweek]);

  return { data, isLoading, error };
}

/**
 * Hook to fetch best value players
 */
export function useBestValuePlayers() {
  const [data, setData] = useState<BestValueData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    fetch(`${API_BASE}/api/top100/best-value/`, {
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: BestValueData = await response.json();
        if (isMounted) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load best value players", err);
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
  }, []);

  return { data, isLoading, error };
}

/**
 * Hook to fetch Top 100 points chart data with optional user overlay
 */
export function useTop100Chart(entryId?: number, startGw: number = 1, endGw?: number) {
  const [data, setData] = useState<Top100ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChart = useCallback(async (entry?: number) => {
    setIsLoading(true);
    
    const params = new URLSearchParams();
    params.append("start_gw", startGw.toString());
    if (endGw) params.append("end_gw", endGw.toString());
    if (entry) params.append("entry_id", entry.toString());

    try {
      const response = await fetch(
        `${API_BASE}/api/top100/chart/?${params.toString()}`,
        { headers: { Accept: "application/json" } }
      );
      
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      
      const payload: Top100ChartData = await response.json();
      setData(payload);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load chart data", err);
      setError(err.message ?? "Unexpected error");
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [startGw, endGw]);

  useEffect(() => {
    fetchChart(entryId);
  }, [entryId, fetchChart]);

  return { data, isLoading, error, refetch: fetchChart };
}

/**
 * Hook to fetch Top 100 transfer trends
 */
export function useTop100Transfers(gameweek?: number) {
  const [data, setData] = useState<Top100TransfersData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    const url = gameweek
      ? `${API_BASE}/api/top100/transfers/?gameweek=${gameweek}`
      : `${API_BASE}/api/top100/transfers/`;

    fetch(url, { headers: { Accept: "application/json" } })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: Top100TransfersData = await response.json();
        if (isMounted) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load transfer trends", err);
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
  }, [gameweek]);

  return { data, isLoading, error };
}

/**
 * Hook to fetch Top 100 differential picks
 */
export function useTop100Differentials(gameweek?: number, maxOwnership: number = 15) {
  const [data, setData] = useState<Top100DifferentialsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    const params = new URLSearchParams();
    if (gameweek) params.append("gameweek", gameweek.toString());
    params.append("max_ownership", maxOwnership.toString());

    fetch(`${API_BASE}/api/top100/differentials/?${params.toString()}`, {
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: Top100DifferentialsData = await response.json();
        if (isMounted) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load differentials", err);
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
  }, [gameweek, maxOwnership]);

  return { data, isLoading, error };
}
