import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return <div className="mb-4 animate-bounce text-8xl">👨‍🏫</div>;
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({ startButtonText, onStartCall, ref }: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-red-50 to-amber-50 text-center dark:from-red-950/20 dark:to-amber-950/20">
        <WelcomeImage />

        <h1 className="mb-2 text-3xl font-bold text-red-800 md:text-4xl dark:text-red-400">Asian Parent Math Tutor</h1>

        <p className="text-foreground max-w-prose px-4 pt-1 text-lg leading-6 font-medium">
          &quot;Why you no doctor yet? At least get A+ in math first!&quot;
        </p>

        <p className="text-muted-foreground mt-2 px-4 text-sm italic">
          Aiya! Don&apos;t just stand there, start your session!
        </p>

        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          className="mt-8 w-72 bg-red-600 font-mono text-lg hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800"
        >
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose px-4 pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Need help? Your cousin already knows how to use this.{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://docs.livekit.io/agents/start/voice-ai/"
            className="underline hover:text-red-600 dark:hover:text-red-400"
          >
            Read the docs lah!
          </a>
        </p>
      </div>
    </div>
  );
};
