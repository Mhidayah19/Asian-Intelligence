'use client';

import { useMemo } from 'react';
import { Track } from 'livekit-client';
import { BarVisualizer, useLocalParticipant, useVoiceAssistant } from '@livekit/components-react';
import type { TrackReference } from '@livekit/components-react';
import { cn } from '@/lib/utils';

export type Mood = 'happy' | 'neutral' | 'disappointed' | 'angry';

interface AgentAvatarCardProps {
  mood?: Mood;
  className?: string;
}

const MOOD_CONFIG: Record<
  Mood,
  { emoji: string; label: string; bgColor: string; textColor: string }
> = {
  happy: {
    emoji: '😊',
    label: 'Pleased (rare)',
    bgColor: 'bg-green-100 dark:bg-green-900/20',
    textColor: 'text-green-700 dark:text-green-400',
  },
  neutral: {
    emoji: '😐',
    label: 'Watching...',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/20',
    textColor: 'text-yellow-700 dark:text-yellow-400',
  },
  disappointed: {
    emoji: '😤',
    label: 'Disappointed',
    bgColor: 'bg-orange-100 dark:bg-orange-900/20',
    textColor: 'text-orange-700 dark:text-orange-400',
  },
  angry: {
    emoji: '😠',
    label: 'Very Upset!',
    bgColor: 'bg-red-100 dark:bg-red-900/20',
    textColor: 'text-red-700 dark:text-red-400',
  },
};

export function AgentAvatarCard({ mood = 'neutral', className }: AgentAvatarCardProps) {
  const config = MOOD_CONFIG[mood];
  const { state: agentState } = useVoiceAssistant();

  // Get user's microphone track (like the microphone button does)
  const { localParticipant } = useLocalParticipant();
  const micPublication = localParticipant.getTrackPublication(Track.Source.Microphone);
  const micTrackRef = useMemo<TrackReference | undefined>(
    () =>
      micPublication
        ? {
            source: Track.Source.Microphone,
            participant: localParticipant,
            publication: micPublication,
          }
        : undefined,
    [micPublication, localParticipant]
  );

  return (
    <div
      className={cn(
        'dark:bg-card rounded-lg border border-red-200 bg-white p-4 shadow-md dark:border-red-900/30',
        className
      )}
    >
      <div className="text-center">
        {/* Avatar with mood */}
        <div
          className={cn(
            'mb-3 inline-flex h-24 w-24 items-center justify-center rounded-full transition-all duration-300',
            config.bgColor
          )}
        >
          <span className="text-6xl">{config.emoji}</span>
        </div>

        <div className={cn('mb-1 text-sm font-semibold', config.textColor)}>{config.label}</div>

        <div className="text-xs text-gray-500 italic dark:text-gray-400">Asian Parent Mode</div>
      </div>

      {/* Audio Waveform Visualizer */}
      <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/30 dark:bg-amber-950/20">
        <div className="mb-2 text-center text-xs font-semibold text-gray-600 dark:text-gray-400">
          Voice Activity
        </div>
        <BarVisualizer
          barCount={7}
          state={agentState}
          options={{ minHeight: 8 }}
          trackRef={micTrackRef}
          className={cn('flex h-16 items-center justify-center gap-1.5')}
        >
          <span
            className={cn([
              'min-h-2 w-2 rounded-full bg-red-300 dark:bg-red-700',
              'origin-center transition-all duration-200 ease-linear',
              'data-[lk-highlighted=true]:bg-red-600 dark:data-[lk-highlighted=true]:bg-red-500',
              'data-[lk-highlighted=true]:h-8',
              'data-[lk-muted=true]:bg-gray-300 dark:data-[lk-muted=true]:bg-gray-700',
            ])}
          />
        </BarVisualizer>
        <div className="mt-2 text-center text-[10px] text-gray-500 italic dark:text-gray-500">
          {agentState === 'speaking'
            ? 'Speaking...'
            : agentState === 'listening'
              ? 'Listening...'
              : agentState === 'thinking'
                ? 'Thinking...'
                : 'Ready'}
        </div>
      </div>
    </div>
  );
}
