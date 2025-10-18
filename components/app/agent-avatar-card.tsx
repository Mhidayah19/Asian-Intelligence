'use client';

import { useMemo } from 'react';
import { Track } from 'livekit-client';
import { cn } from '@/lib/utils';
import { BarVisualizer, useLocalParticipant, useVoiceAssistant } from '@livekit/components-react';
import type { TrackReference } from '@livekit/components-react';

export type Mood = 'happy' | 'neutral' | 'disappointed' | 'angry';

interface AgentAvatarCardProps {
  mood?: Mood;
  className?: string;
}

const MOOD_CONFIG: Record<Mood, { emoji: string; label: string; bgColor: string; textColor: string }> = {
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
    () => (micPublication ? { source: Track.Source.Microphone, participant: localParticipant, publication: micPublication } : undefined),
    [micPublication, localParticipant]
  );

  return (
    <div className={cn('bg-white dark:bg-card rounded-lg p-4 shadow-md border border-red-200 dark:border-red-900/30', className)}>
      
      <div className="text-center">
        {/* Avatar with mood */}
        <div className={cn('inline-flex items-center justify-center w-24 h-24 rounded-full mb-3 transition-all duration-300', config.bgColor)}>
          <span className="text-6xl">{config.emoji}</span>
        </div>
        
        <div className={cn('text-sm font-semibold mb-1', config.textColor)}>
          {config.label}
        </div>
        
        <div className="text-xs text-gray-500 dark:text-gray-400 italic">
          Asian Parent Mode
        </div>
      </div>
      
      {/* Audio Waveform Visualizer */}
      <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-950/20 rounded-md border border-amber-200 dark:border-amber-900/30">
        <div className="text-xs text-gray-600 dark:text-gray-400 font-semibold mb-2 text-center">
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
              'bg-red-300 dark:bg-red-700 min-h-2 w-2 rounded-full',
              'origin-center transition-all duration-200 ease-linear',
              'data-[lk-highlighted=true]:bg-red-600 dark:data-[lk-highlighted=true]:bg-red-500',
              'data-[lk-highlighted=true]:h-8',
              'data-[lk-muted=true]:bg-gray-300 dark:data-[lk-muted=true]:bg-gray-700',
            ])}
          />
        </BarVisualizer>
        <div className="text-[10px] text-gray-500 dark:text-gray-500 text-center mt-2 italic">
          {agentState === 'speaking' ? 'Speaking...' : 
           agentState === 'listening' ? 'Listening...' : 
           agentState === 'thinking' ? 'Thinking...' : 
           'Ready'}
        </div>
      </div>
    </div>
  );
}

