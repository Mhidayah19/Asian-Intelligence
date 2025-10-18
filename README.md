# Asian Intelligence - Voice AI Platform

A real-time voice AI application powered by [LiveKit](https://livekit.io) and OpenAI's Realtime API. Built with Next.js 15 and Python.

## 🚀 Quick Start

**See [QUICKSTART.md](./QUICKSTART.md) for detailed setup instructions.**

### Run the Application

**Terminal 1 - Start the Agent:**
```bash
./start-agent.sh
```

**Terminal 2 - Start the Frontend:**
```bash
./start-frontend.sh
```

Then open http://localhost:3000 and start talking!

Also available for:
[Android](https://github.com/livekit-examples/agent-starter-android) • [Flutter](https://github.com/livekit-examples/agent-starter-flutter) • [Swift](https://github.com/livekit-examples/agent-starter-swift) • [React Native](https://github.com/livekit-examples/agent-starter-react-native)

<picture>
  <source srcset="./.github/assets/readme-hero-dark.webp" media="(prefers-color-scheme: dark)">
  <source srcset="./.github/assets/readme-hero-light.webp" media="(prefers-color-scheme: light)">
  <img src="./.github/assets/readme-hero-light.webp" alt="App screenshot">
</picture>

### Features:

- Real-time voice interaction with LiveKit Agents
- Camera video streaming support
- Screen sharing capabilities
- Audio visualization and level monitoring
- Virtual avatar integration
- Light/dark theme switching with system preference detection
- Customizable branding, colors, and UI text via configuration

This template is built with Next.js and is free for you to use or modify as you see fit.

### Project Structure

```
Asian-Intelligence/
├── agent/                    # Python Voice AI Backend
│   ├── src/agent.py         # Main agent logic (OpenAI Realtime API)
│   └── .env.local           # Agent configuration
├── app/                     # Next.js App Router
│   ├── (app)/              # App pages
│   └── api/                # API routes
├── components/             # React components
│   ├── app/               # App-specific components
│   └── livekit/           # LiveKit UI components
├── hooks/                 # Custom React hooks
├── start-agent.sh        # 🤖 Start backend
├── start-frontend.sh     # 🌐 Start frontend
└── .env.local           # Frontend configuration
```

## Configuration

This starter is designed to be flexible so you can adapt it to your specific agent use case. You can easily configure it to work with different types of inputs and outputs:

#### Example: App configuration (`app-config.ts`)

```ts
export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'LiveKit',
  pageTitle: 'LiveKit Voice Agent',
  pageDescription: 'A voice agent built with LiveKit',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#002cf2',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#1fd5f9',
  startButtonText: 'Start call',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
```

You can update these values in [`app-config.ts`](./app-config.ts) to customize branding, features, and UI text for your deployment.

> [!NOTE]
> The `sandboxId` and `agentName` are for the LiveKit Cloud Sandbox environment.
> They are not used for local development.

#### Environment Variables

You'll also need to configure your LiveKit credentials in `.env.local` (copy `.env.example` if you don't have one):

```env
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=https://your-livekit-server-url
```

These are required for the voice agent functionality to work with your LiveKit project.

## Contributing

This template is open source and we welcome contributions! Please open a PR or issue through GitHub, and don't forget to join us in the [LiveKit Community Slack](https://livekit.io/join-slack)!
