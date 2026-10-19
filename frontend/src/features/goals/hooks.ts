import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { goalsApi } from './api';
import type { ContributionInput, GoalInput } from './types';

export const useGoals = () => useQuery({ queryKey: ['goals', 'list'], queryFn: goalsApi.list });

export const useContributions = (goalId: string | undefined) =>
  useQuery({ queryKey: ['goals', 'contributions', goalId], queryFn: () => goalsApi.contributions(goalId!), enabled: !!goalId });

function useInvalidateGoals() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ['goals'] });
}

export function useCreateGoal() {
  const inv = useInvalidateGoals();
  return useMutation({ mutationFn: (b: GoalInput) => goalsApi.create(b), onSuccess: inv });
}

export function useUpdateGoal() {
  const inv = useInvalidateGoals();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<GoalInput>) => goalsApi.update(id, body),
    onSuccess: inv,
  });
}

export function useDeleteGoal() {
  const inv = useInvalidateGoals();
  return useMutation({ mutationFn: (id: string) => goalsApi.remove(id), onSuccess: inv });
}

export function useAddContribution() {
  const inv = useInvalidateGoals();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & ContributionInput) => goalsApi.addContribution(id, body),
    onSuccess: inv,
  });
}

export function useRemoveContribution() {
  const inv = useInvalidateGoals();
  return useMutation({
    mutationFn: ({ id, cid }: { id: string; cid: string }) => goalsApi.removeContribution(id, cid),
    onSuccess: inv,
  });
}
