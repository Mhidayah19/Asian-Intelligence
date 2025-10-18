'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';

export type Mood = 'happy' | 'neutral' | 'disappointed' | 'angry';

interface AsianParentAvatarProps {
  mood?: Mood;
  className?: string;
  showPopOutButton?: boolean;
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

export function AsianParentAvatar({ mood = 'neutral', className, showPopOutButton = false }: AsianParentAvatarProps) {
  const config = MOOD_CONFIG[mood];
  const [isPoppedOut, setIsPoppedOut] = useState(false);

  const handlePopOut = async () => {
    // @ts-ignore - Document PiP API is experimental
    if (!window.documentPictureInPicture) {
      alert('Picture-in-Picture not supported. Use Chrome 116+');
      return;
    }

    try {
      // @ts-ignore
      const pipWindow = await window.documentPictureInPicture.requestWindow({
        width: 360,
        height: 400,
      });

      // Copy styles to PiP window
      [...document.styleSheets].forEach((styleSheet) => {
        try {
          const cssRules = [...styleSheet.cssRules].map((rule) => rule.cssText).join('');
          const style = document.createElement('style');
          style.textContent = cssRules;
          pipWindow.document.head.appendChild(style);
        } catch (e) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = styleSheet.href!;
          pipWindow.document.head.appendChild(link);
        }
      });

      // Clone the avatar into PiP window
      const avatarHTML = `
        <div style="padding: 16px; background: white; height: 100vh;">
          <div style="background: white; border-radius: 8px; padding: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #fecaca;">
            <div style="text-align: center;">
              <div style="display: inline-flex; align-items: center; justify-content: center; width: 96px; height: 96px; border-radius: 50%; margin-bottom: 12px; ${config.bgColor.includes('green') ? 'background: #dcfce7;' : config.bgColor.includes('yellow') ? 'background: #fef3c7;' : config.bgColor.includes('orange') ? 'background: #ffedd5;' : 'background: #fee2e2;'}">
                <span style="font-size: 4rem;">${config.emoji}</span>
              </div>
              <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 4px; ${config.textColor.includes('green') ? 'color: #15803d;' : config.textColor.includes('yellow') ? 'color: #a16207;' : config.textColor.includes('orange') ? 'color: #c2410c;' : 'color: #b91c1c;'}">
                ${config.label}
              </div>
              <div style="font-size: 0.75rem; color: #6b7280; font-style: italic;">
                Asian Parent Mode
              </div>
            </div>
            <div style="margin-top: 16px; padding: 12px; background: #fffbeb; border-radius: 6px; border: 1px solid #fcd34d;">
              <p style="font-size: 0.75rem; color: #374151; font-style: italic; line-height: 1.625;">
                ${mood === 'happy' ? "Not bad lah... but don't get cocky!" : mood === 'neutral' ? "I'm watching you. Better focus!" : mood === 'disappointed' ? "Aiya! Your cousin would never make this mistake!" : "WALAO! You want to become garbage collector ah?!"}
              </p>
            </div>
          </div>
        </div>
      `;

      pipWindow.document.body.innerHTML = avatarHTML;
      setIsPoppedOut(true);

      // Reset when closed
      // @ts-ignore
      pipWindow.addEventListener('pagehide', () => {
        setIsPoppedOut(false);
      });
    } catch (error) {
      console.error('PiP failed:', error);
      alert('Failed to open Picture-in-Picture window');
    }
  };

  return (
    <div className={cn('bg-white dark:bg-card rounded-lg p-4 shadow-md border border-red-200 dark:border-red-900/30', className)}>
      {showPopOutButton && !isPoppedOut && (
        <button
          onClick={handlePopOut}
          className="mb-3 w-full px-3 py-2 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
        >
          👁️ Pop Out (Always On Top)
        </button>
      )}
      {isPoppedOut && (
        <div className="mb-3 px-3 py-2 text-xs text-center text-green-700 bg-green-100 rounded-md">
          ✓ Watching in PiP window
        </div>
      )}
      <div className="text-center">
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
      
      {/* Mood-specific quotes */}
      <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-950/20 rounded-md border border-amber-200 dark:border-amber-900/30">
        <p className="text-xs text-gray-700 dark:text-gray-300 italic leading-relaxed">
          {mood === 'happy' && "Not bad lah... but don't get cocky!"}
          {mood === 'neutral' && "I'm watching you. Better focus!"}
          {mood === 'disappointed' && "Aiya! Your cousin would never make this mistake!"}
          {mood === 'angry' && "WALAO! You want to become garbage collector ah?!"}
        </p>
      </div>
    </div>
  );
}

