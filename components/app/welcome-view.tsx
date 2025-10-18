import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <div className="mb-4 text-8xl animate-bounce">
      👨‍🏫
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-gradient-to-br from-red-50 to-amber-50 dark:from-red-950/20 dark:to-amber-950/20 flex flex-col items-center justify-center text-center min-h-screen">
        <WelcomeImage />

        <h1 className="text-3xl md:text-4xl font-bold text-red-800 dark:text-red-400 mb-2">
          Asian Parent Math Tutor
        </h1>

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium text-lg px-4">
          "Why you no doctor yet? At least get A+ in math first!"
        </p>

        <p className="text-muted-foreground text-sm mt-2 italic px-4">
          Aiya! Don't just stand there, start your session!
        </p>

        <Button 
          variant="primary" 
          size="lg" 
          onClick={onStartCall} 
          className="mt-8 w-72 font-mono text-lg bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800"
        >
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm px-4">
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
