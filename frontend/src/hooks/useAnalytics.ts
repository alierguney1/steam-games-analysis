import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => {
      const response = await api.dashboard.summary();
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useGames(params?: any) {
  return useQuery({
    queryKey: ['games', params],
    queryFn: async () => {
      const response = await api.games.list(params);
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });
}

export function useGame(id: number) {
  return useQuery({
    queryKey: ['game', id],
    queryFn: async () => {
      const response = await api.games.get(id);
      return response.data;
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  });
}

export function useDiDAnalysis(params?: any) {
  return useQuery({
    queryKey: ['analytics', 'did', params],
    queryFn: async () => {
      const response = await api.analytics.did(params);
      return response.data;
    },
    staleTime: 1000 * 60 * 10,
  });
}

export function useSurvivalAnalysis(params?: any) {
  return useQuery({
    queryKey: ['analytics', 'survival', params],
    queryFn: async () => {
      const response = await api.analytics.survival(params);
      return response.data;
    },
    staleTime: 1000 * 60 * 10,
  });
}

export function useElasticityAnalysis(params?: any) {
  return useQuery({
    queryKey: ['analytics', 'elasticity', params],
    queryFn: async () => {
      const response = await api.analytics.elasticity(params);
      return response.data;
    },
    staleTime: 1000 * 60 * 10,
  });
}

export function useIngestionStatus() {
  return useQuery({
    queryKey: ['ingestion', 'status'],
    queryFn: async () => {
      const response = await api.ingestion.status();
      return response.data;
    },
    refetchInterval: 1000 * 30, // Refresh every 30 seconds
    staleTime: 1000 * 10,
  });
}
