export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Asian Intelligence',
  pageTitle: 'Asian Parent Math Tutor AI',
  pageDescription: 'An AI tutor that helps with math in the style of an Asian tiger parent - "Why you get B+? You want to be failure in life ah?"',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg', // TODO: Replace with Asian parent avatar icon
  accent: '#dc2626', // Red theme for Asian parent intensity
  logoDark: '/lk-logo-dark.svg', // TODO: Replace with dark version
  accentDark: '#f87171', // Lighter red for dark mode
  startButtonText: 'Start Math Tutoring Session',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: 'asian-parent-tutor',
};
