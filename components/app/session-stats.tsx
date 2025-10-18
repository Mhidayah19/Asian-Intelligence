'use client';

import { cn } from '@/lib/utils';

interface SessionStatsProps {
  className?: string;
}

// Mock data - will be replaced with real data from agent later
const MOCK_STATS = {
  mistakes: 3,
  correct: 7,
  cousinName: 'Marcus',
  cousinScore: 'A++',
};

export function SessionStats({ className }: SessionStatsProps) {
  return (
    <div className={cn('bg-white dark:bg-card rounded-lg p-4 shadow-md border border-red-200 dark:border-red-900/30', className)}>
      <h3 className="font-semibold text-red-800 dark:text-red-400 mb-3 text-lg">
        📋 Report Card
      </h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between items-center">
          <span className="text-gray-700 dark:text-gray-300">Mistakes:</span>
          <span className="font-bold text-red-600 dark:text-red-400">
            {MOCK_STATS.mistakes} 😤
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-700 dark:text-gray-300">Correct:</span>
          <span className="font-bold text-gray-700 dark:text-gray-300">
            {MOCK_STATS.correct} 😐
          </span>
        </div>
        <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
            Cousin {MOCK_STATS.cousinName}'s Score:
          </div>
          <div className="font-bold text-amber-600 dark:text-amber-400">
            {MOCK_STATS.cousinScore} ⭐
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 italic mt-1">
            (always better)
          </div>
        </div>
      </div>
    </div>
  );
}

