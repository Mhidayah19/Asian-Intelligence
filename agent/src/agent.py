import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai, silero

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful and enthusiastic AI assistant.
            The user is interacting with you via voice.
            Keep your responses concise, clear, and conversational.
            Be friendly and speak naturally.""",
        )


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    # Initialize OpenAI Realtime model (handles STT, LLM, and TTS)
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="alloy",  # Available: alloy, echo, fable, onyx, nova, shimmer
            temperature=0.8,
        )
    )

    # Start the session and connect to the room
    await session.start(agent=Assistant(), room=ctx.room)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
